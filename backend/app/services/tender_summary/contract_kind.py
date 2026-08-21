"""Detect contract kind for field applicability rules (US 1.4)."""
from __future__ import annotations

import enum
import re
import unicodedata
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, not_, or_

from app.models.tender import Tender

if TYPE_CHECKING:
    from sqlalchemy.orm import Query


class ContractKind(str, enum.Enum):
    EJECUCION_OBRA = "ejecucion_obra"
    INTERVENTORIA = "interventoria"
    ESTUDIOS_DISENOS = "estudios_disenos"
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
    "concurso de meritos",
    "concurso de méritos",
)
_OBRA = (
    "ejecucion de obra",
    "ejecución de obra",
    "licitacion de obra",
    "licitación de obra",
    "obra publica",
    "obra pública",
    "construccion",
    "construcción",
    "mejoramiento",
    "paviment",
    " adoquin",
    " adoquín",
    "boxculvert",
    "box culvert",
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


def detect_contract_kind(tender: Tender) -> ContractKind:
    """Classify tender by business category (filter groups)."""
    haystack = _tender_haystack(tender)
    has_interventoria = _contains_any(haystack, _INTERVENTORIA)
    has_obra = _contains_any(haystack, _OBRA)
    has_estudios = _contains_any(haystack, _ESTUDIOS)

    if has_interventoria:
        return ContractKind.INTERVENTORIA
    if has_obra:
        return ContractKind.EJECUCION_OBRA
    if has_estudios:
        return ContractKind.ESTUDIOS_DISENOS
    return ContractKind.DESCONOCIDO


def contract_kind_label(kind: ContractKind) -> str:
    labels = {
        ContractKind.EJECUCION_OBRA: "Ejecución de obra",
        ContractKind.INTERVENTORIA: "Interventoría",
        ContractKind.ESTUDIOS_DISENOS: "Estudios y diseños",
        ContractKind.DESCONOCIDO: "No identificado",
    }
    return labels[kind]


def aiu_applies(kind: ContractKind) -> bool:
    return kind == ContractKind.EJECUCION_OBRA


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


def apply_contract_kind_filter(query: "Query", kind: ContractKind) -> "Query":
    """Filter tenders using the same category rules as detect_contract_kind."""
    haystack = _sql_haystack()
    interventoria = _sql_contains_any(haystack, _INTERVENTORIA)
    obra = _sql_contains_any(haystack, _OBRA)
    estudios = _sql_contains_any(haystack, _ESTUDIOS)

    if kind == ContractKind.INTERVENTORIA:
        return query.filter(interventoria)
    if kind == ContractKind.EJECUCION_OBRA:
        return query.filter(and_(obra, not_(interventoria)))
    if kind == ContractKind.ESTUDIOS_DISENOS:
        return query.filter(and_(estudios, not_(interventoria), not_(obra)))
    return query


def parse_contract_kind(value: str | None) -> ContractKind | None:
    if not value:
        return None
    try:
        return ContractKind(value)
    except ValueError:
        return None
