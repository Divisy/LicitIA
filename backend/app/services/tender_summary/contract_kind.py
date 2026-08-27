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
_ESTUDIOS_DISENOS_ENUNCIADO = (
    "estudios y dise",
    "estudio y dise",
    "estudios, dise",
    "estudio, dise",
    "los estudios",
    "elaboracion de estudios",
    "actualizacion de estudios",
    "disenos complementarios",
    "diseños complementarios",
    "disenos definitivos",
    "diseños definitivos",
    "diseno",
    "diseño",
    "factibilidad",
    "prefactibilidad",
    "consultoria",
    "consultoría",
    "ingenieria de detalle",
    "ingeniería de detalle",
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


def _object_haystack(tender: Tender) -> str:
    return _normalize(tender.object_text or "")


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


def has_estudios_disenos_en_enunciado(tender: Tender) -> bool:
    """True when the tender object mentions studies and/or designs."""
    return _contains_any(_object_haystack(tender), _ESTUDIOS_DISENOS_ENUNCIADO)


def is_estudios_disenos_y_obra(tender: Tender) -> bool:
    """
    Licitación pública Obra Pública whose object includes estudios and/or diseños.

    Pure obra (same modality, no estudios/diseños in enunciado) stays ejecucion_obra.
    """
    if _contains_any(_tender_haystack(tender), _INTERVENTORIA):
        return False
    if not is_licitacion_obra_publica(tender.contract_modality):
        return False
    return has_estudios_disenos_en_enunciado(tender)


def detect_contract_kind(tender: Tender) -> ContractKind:
    """Classify tender by SECOP process type and object (filter groups)."""
    modality = tender.contract_modality
    haystack = _tender_haystack(tender)

    if _contains_any(haystack, _INTERVENTORIA):
        return ContractKind.INTERVENTORIA

    if is_estudios_disenos_y_obra(tender):
        return ContractKind.ESTUDIOS_DISENOS_Y_OBRA

    if is_licitacion_obra_publica(modality):
        return ContractKind.EJECUCION_OBRA

    if (
        is_concurso_meritos(modality)
        or is_consultoria_contract_type(tender.contract_type)
        or _contains_any(haystack, _ESTUDIOS_DISENOS_ENUNCIADO)
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


def _sql_object_text():
    return func.lower(func.coalesce(Tender.object_text, ""))


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
    object_text = _sql_object_text()
    haystack = _sql_haystack()
    estudios_enunciado = _sql_contains_any(object_text, _ESTUDIOS_DISENOS_ENUNCIADO)
    interventoria = _sql_contains_any(haystack, _INTERVENTORIA)
    return and_(
        _sql_licitacion_obra_publica(),
        estudios_enunciado,
        not_(interventoria),
    )


def apply_contract_kind_filter(query: "Query", kind: ContractKind) -> "Query":
    """Filter tenders using the same category rules as detect_contract_kind."""
    haystack = _sql_haystack()
    obra_modality = _sql_licitacion_obra_publica()
    interventoria = _sql_contains_any(haystack, _INTERVENTORIA)
    estudios_kw = _sql_contains_any(haystack, _ESTUDIOS_DISENOS_ENUNCIADO)
    concurso = _sql_concurso_meritos()
    consultoria = _sql_consultoria_type()
    hybrid = _sql_hybrid_estudios_obra()

    if kind == ContractKind.ESTUDIOS_DISENOS_Y_OBRA:
        return query.filter(hybrid)
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
