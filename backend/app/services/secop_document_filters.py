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
            "formulario 1",
            "propuesta economica",
            "propuesta económica",
            "formulario economico",
            "formulario económico",
            "ppto",
            "apu",
            "analisis de precios",
            "análisis de precios",
            "oferta economica",
            "oferta económica",
        ),
    ),
]

# Word-level fallbacks when no phrase keyword matches (order: pliego → anexo → presupuesto).
_FALLBACK_RULES: list[tuple[DocumentType, tuple[re.Pattern[str], ...]]] = [
    (
        DocumentType.PLIEGO_CONDICIONES,
        (re.compile(r"\bpliegos?\b"),),
    ),
    (
        DocumentType.ANEXO_TECNICO,
        (
            re.compile(r"\banexos?\b"),
            re.compile(r"\btecnicos?\b"),
            re.compile(r"\btecnicas?\b"),
        ),
    ),
    (
        DocumentType.PRESUPUESTO,
        (
            re.compile(r"\bpresupuestos?\b"),
            re.compile(r"\beconomicas?\b"),
            re.compile(r"\bprecios\b"),
            re.compile(r"\bppto\b"),
            re.compile(r"\bapu\b"),
            re.compile(r"\beconomicos?\b"),
        ),
    ),
]


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_document_filename(file_name: str) -> str:
    """Normalize a filename for duplicate detection across SECOP catalog versions."""
    return _normalize_text(file_name)


def classify_document(filename: str, description: Optional[str] = None) -> DocumentType:
    """Classify a SECOP document by filename and optional description."""
    haystack = _normalize_text(f"{filename} {description or ''}")

    for doc_type, keywords in _KEYWORD_RULES:
        if any(keyword in haystack for keyword in keywords):
            return doc_type

    for doc_type, patterns in _FALLBACK_RULES:
        if any(pattern.search(haystack) for pattern in patterns):
            return doc_type

    return DocumentType.OTRO


def is_key_document(doc_type: DocumentType) -> bool:
    """Return True for pliego, anexo técnico and presupuesto."""
    return doc_type != DocumentType.OTRO
