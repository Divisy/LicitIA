"""Detect contract kind for field applicability rules (US 1.4)."""
from __future__ import annotations

import enum
import re
import unicodedata
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, not_, or_

from app.models.tender import Tender
from app.services.secop_filters import (
    MODALITY_CONCURSO_MERITOS_ABIERTO,
    MODALITY_LICITACION_OBRA_PUBLICA,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Query


class ContractKind(str, enum.Enum):
    EJECUCION_OBRA = "ejecucion_obra"
    INTERVENTORIA = "interventoria"
    ESTUDIOS_DISENOS = "estudios_disenos"
    ESTUDIOS_DISENOS_Y_OBRA = "estudios_disenos_y_obra"
    DESCONOCIDO = "desconocido"


_INTERVENTORIA = (
    "interventoria",
    "interventoría",
    "supervision",
    "supervisión",
    "supervisar",
    "control de obra",
    "fiscalizacion",
    "fiscalización",
)
_ESTUDIOS = (
    "estudios y dise",
    "estudio y dise",
    "consultoria",
    "consultoría",
    "diseno",
    "diseño",
    "ingenieria de detalle",
    "ingeniería de detalle",
    "prefactibilidad",
    "factibilidad",
)
_OBRA_EJECUCION = (
    "construccion",
    "construir",
    "culminacion de las obras",
    "culminacion de obra",
    "ejecucion de las obras",
    "ejecucion de obra",
    "ejecucion de la obra",
    "realizacion de las obras",
    "realizacion de obra",
    "puesta en marcha",
)
# Estudios/diseños y ejecución de obra listados como entregables del mismo contrato.
_HYBRID_ESTUDIOS_OBRA_RE = re.compile(
    r"estudios?.{0,60}(?:y|,).{0,60}"
    r"(?:disenos?.{0,60}(?:y|,).{0,60})?"
    r"(?:construcc|culminacion|ejecucion|realizacion)",
    re.DOTALL,
)
_HYBRID_DISENOS_OBRA_RE = re.compile(
    r"disenos?.{0,60}(?:y|,).{0,60}(?:construcc|culminacion|ejecucion|realizacion)",
    re.DOTALL,
)
_HYBRID_MEJORAMIENTO_SOLO_ESTUDIOS_RE = re.compile(
    r"para el mejoramiento.{0,120}construccion de placa",
    re.DOTALL,
)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return f" {text.strip()} "


def _tender_haystack(tender: Tender) -> str:
    parts = [
        tender.object_text or "",
        tender.contract_type or "",
        tender.contract_modality or "",
        tender.reference or "",
    ]
    return _normalize(" ".join(parts))


def _contains_any(haystack: str, tokens: tuple[str, ...]) -> bool:
    return any(token in haystack for token in tokens)


def is_licitacion_obra_publica(modality: str | None) -> bool:
    """True for SECOP modalidad 'Licitación pública Obra Publica' (tipo de proceso obra)."""
    norm = _normalize(modality or "")
    return "licitacion publica" in norm and "obra publica" in norm


def is_concurso_meritos(modality: str | None) -> bool:
    norm = _normalize(modality or "")
    return "concurso de meritos" in norm


def is_consultoria_contract_type(contract_type: str | None) -> bool:
    norm = _normalize(contract_type or "")
    return "consultoria" in norm


def is_estudios_disenos_y_obra(haystack: str) -> bool:
    """True when the object contracts studies/designs and obra execution in the same process."""
    if _contains_any(haystack, _INTERVENTORIA):
        return False
    if _HYBRID_MEJORAMIENTO_SOLO_ESTUDIOS_RE.search(haystack):
        return False
    if _HYBRID_ESTUDIOS_OBRA_RE.search(haystack):
        return True
    if _HYBRID_DISENOS_OBRA_RE.search(haystack):
        return True
    if re.search(
        r"elaboracion de estudios.{0,80}(?:construcc|culminacion|ejecucion|realizacion)",
        haystack,
    ):
        return True
    if re.search(
        r"contratar los estudios.{0,100}(?:construcc|culminacion|ejecucion|realizacion)",
        haystack,
    ):
        return True
    if re.search(
        r"actualizacion de estudios.{0,80}(?:construcc|culminacion|ejecucion|realizacion)",
        haystack,
    ):
        return True
    if _contains_any(haystack, _ESTUDIOS) and _contains_any(haystack, _OBRA_EJECUCION):
        if re.search(
            r"(?:culminacion|ejecucion|realizacion).{0,30}(?:de las )?obras?\b",
            haystack,
        ):
            return True
    return False


def detect_contract_kind(tender: Tender) -> ContractKind:
    """Classify tender by SECOP process type and object (filter groups)."""
    modality = tender.contract_modality
    haystack = _tender_haystack(tender)

    if _contains_any(haystack, _INTERVENTORIA):
        return ContractKind.INTERVENTORIA

    if is_estudios_disenos_y_obra(haystack):
        return ContractKind.ESTUDIOS_DISENOS_Y_OBRA

    if is_licitacion_obra_publica(modality):
        return ContractKind.EJECUCION_OBRA

    if (
        is_concurso_meritos(modality)
        or is_consultoria_contract_type(tender.contract_type)
        or _contains_any(haystack, _ESTUDIOS)
    ):
        return ContractKind.ESTUDIOS_DISENOS

    return ContractKind.DESCONOCIDO


def contract_kind_label(kind: ContractKind) -> str:
    labels = {
        ContractKind.EJECUCION_OBRA: "Ejecución de obra",
        ContractKind.INTERVENTORIA: "Interventoría",
        ContractKind.ESTUDIOS_DISENOS: "Estudios y diseños",
        ContractKind.ESTUDIOS_DISENOS_Y_OBRA: "Estudios, diseños y obra",
        ContractKind.DESCONOCIDO: "No identificado",
    }
    return labels[kind]


def aiu_applies(kind: ContractKind) -> bool:
    return kind in (
        ContractKind.EJECUCION_OBRA,
        ContractKind.ESTUDIOS_DISENOS_Y_OBRA,
    )


def _sql_haystack():
    return func.lower(
        func.concat(
            Tender.object_text,
            " ",
            func.coalesce(Tender.contract_type, ""),
            " ",
            func.coalesce(Tender.contract_modality, ""),
            " ",
            func.coalesce(Tender.reference, ""),
        )
    )


def _sql_contains_any(haystack, keywords: tuple[str, ...]):
    return or_(*[haystack.contains(keyword) for keyword in keywords])


def _sql_licitacion_obra_publica():
    modality = func.lower(func.coalesce(Tender.contract_modality, ""))
    return or_(
        Tender.contract_modality == MODALITY_LICITACION_OBRA_PUBLICA,
        and_(
            modality.contains("licitacion publica"),
            modality.contains("obra publica"),
        ),
    )


def _sql_concurso_meritos():
    modality = func.lower(func.coalesce(Tender.contract_modality, ""))
    return or_(
        Tender.contract_modality == MODALITY_CONCURSO_MERITOS_ABIERTO,
        modality.contains("concurso de meritos"),
    )


def _sql_consultoria_type():
    contract_type = func.lower(func.coalesce(Tender.contract_type, ""))
    return contract_type.contains("consultoria")


def _sql_hybrid_estudios_obra():
    haystack = _sql_haystack()
    obra_ejecucion = or_(
        haystack.contains("construccion"),
        haystack.contains("construir"),
        haystack.contains("puesta en marcha"),
        haystack.contains("culminacion de las obras"),
        haystack.contains("culminacion de obra"),
        haystack.contains("ejecucion de las obras"),
        haystack.contains("ejecucion de obra"),
        and_(haystack.contains("culminacion"), haystack.contains("obras")),
        and_(haystack.contains("ejecucion"), haystack.contains("obras")),
    )
    estudios_y_obra = or_(
        and_(haystack.contains("estudios"), haystack.contains("construcc")),
        and_(haystack.contains("diseno"), haystack.contains("construcc")),
        and_(haystack.contains("elaboracion de estudios"), haystack.contains("construcc")),
        and_(haystack.contains("contratar los estudios"), haystack.contains("construcc")),
        and_(haystack.contains("estudios"), haystack.contains("diseno"), haystack.contains("culminacion")),
        and_(haystack.contains("estudios"), haystack.contains("diseno"), haystack.contains("ejecucion")),
        and_(haystack.contains("actualizacion de estudios"), haystack.contains("culminacion")),
        and_(haystack.contains("estudios"), haystack.contains("culminacion")),
    )
    mejoramiento_solo_estudios = and_(
        haystack.contains("para el mejoramiento"),
        haystack.contains("construccion de placa"),
    )
    return and_(obra_ejecucion, estudios_y_obra, not_(mejoramiento_solo_estudios))


def apply_contract_kind_filter(query: "Query", kind: ContractKind) -> "Query":
    """Filter tenders using the same category rules as detect_contract_kind."""
    haystack = _sql_haystack()
    obra_modality = _sql_licitacion_obra_publica()
    interventoria = _sql_contains_any(haystack, _INTERVENTORIA)
    estudios_kw = _sql_contains_any(haystack, _ESTUDIOS)
    concurso = _sql_concurso_meritos()
    consultoria = _sql_consultoria_type()
    hybrid = _sql_hybrid_estudios_obra()

    if kind == ContractKind.ESTUDIOS_DISENOS_Y_OBRA:
        return query.filter(and_(not_(interventoria), hybrid))
    if kind == ContractKind.EJECUCION_OBRA:
        return query.filter(and_(obra_modality, not_(hybrid)))
    if kind == ContractKind.INTERVENTORIA:
        return query.filter(interventoria)
    if kind == ContractKind.ESTUDIOS_DISENOS:
        return query.filter(
            and_(
                not_(interventoria),
                not_(hybrid),
                or_(concurso, consultoria, estudios_kw),
            )
        )
    return query


def parse_contract_kind(value: str | None) -> ContractKind | None:
    if not value:
        return None
    try:
        return ContractKind(value)
    except ValueError:
        return None
