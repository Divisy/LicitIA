"""Document type classification for SECOP tender files (user story 1.2)."""
import enum
import re
import unicodedata
from typing import Optional


class DocumentType(str, enum.Enum):
    """Key document categories required by the MVP."""
    PLIEGO_CONDICIONES = "pliego_condiciones"
    ANEXO_TECNICO = "anexo_tecnico"
    PRESUPUESTO = "presupuesto"
    OTRO = "otro"


_KEYWORD_RULES: list[tuple[DocumentType, tuple[str, ...]]] = [
    (
        DocumentType.PLIEGO_CONDICIONES,
        (
            "pliego de condiciones",
            "pliego condiciones",
            "proyecto de pliego",
            "proyecto de pliegos",
            "proyecto pliego",
            "pliegos definitiv",
            "documento base",
            "prepliego",
            "condiciones definitiv",
        ),
    ),
    (
        DocumentType.ANEXO_TECNICO,
        (
            "anexo tecnico",
            "anexo técnico",
            "anexos tecnicos",
            "anexos de proyecto",
            "anexo de proyecto",
            "especificaciones tecnicas",
            "especificaciones técnicas",
            "especificaciones generales",
            "estudio del sector",
            "analisis del sector",
            "análisis del sector",
        ),
    ),
    (
        DocumentType.PRESUPUESTO,
        (
            "presupuesto",
            "presupuesto oficial",
            "formulario presupuesto",
            "formul1 presupuesto",
            "ppto",
            "apu",
            "analisis de precios",
            "análisis de precios",
            "oferta economica",
            "oferta económica",
        ),
    ),
]


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def classify_document(filename: str, description: Optional[str] = None) -> DocumentType:
    """Classify a SECOP document by filename and optional description."""
    haystack = _normalize_text(f"{filename} {description or ''}")

    for doc_type, keywords in _KEYWORD_RULES:
        if any(keyword in haystack for keyword in keywords):
            return doc_type

    return DocumentType.OTRO


def is_key_document(doc_type: DocumentType) -> bool:
    """Return True for pliego, anexo técnico and presupuesto."""
    return doc_type != DocumentType.OTRO
