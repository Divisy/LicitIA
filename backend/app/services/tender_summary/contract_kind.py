"""Detect contract kind for field applicability rules (US 1.4)."""
from __future__ import annotations

import enum
import re
import unicodedata

from app.models.tender import Tender


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
)
_OBRA = (
    "ejecucion de obra",
    "ejecución de obra",
    "construccion",
    "construcción",
    "mejoramiento",
    "paviment",
    " obra ",
)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return f" {text.strip()} "


def detect_contract_kind(tender: Tender) -> ContractKind:
    """Classify tender contract kind from SECOP metadata."""
    parts = [
        tender.object_text or "",
        tender.contract_type or "",
        tender.contract_modality or "",
        tender.reference or "",
    ]
    haystack = _normalize(" ".join(parts))

    if any(token in haystack for token in _INTERVENTORIA):
        return ContractKind.INTERVENTORIA
    if any(token in haystack for token in _ESTUDIOS):
        return ContractKind.ESTUDIOS_DISENOS
    if any(token in haystack for token in _OBRA):
        return ContractKind.EJECUCION_OBRA
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
