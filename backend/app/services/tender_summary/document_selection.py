"""Pick canonical pliego/presupuesto documents for extraction."""
from __future__ import annotations

from typing import Optional

from app.models.tender_document import TenderDocument
from app.services.secop_document_filters import normalize_document_filename

_PLIEGO_HINTS = (
    "documento base",
    "pliego de condiciones",
    "pliego condiciones",
    "proyecto de pliego",
    "proyecto pliego",
)
_PRESUPUESTO_HINTS = (
    "presupuesto de obra",
    "presupuesto oficial",
    "formulario 1",
    "formul1",
    "propuesta economica",
    "propuesta económica",
    "presupuesto",
)
_PRESUPUESTO_FILENAME_REJECT = (
    "pliego",
    "documento base",
    "condiciones",
    "estudios previos",
    "anexo tecnico",
    "anexo técnico",
)


def is_presupuesto_source_document(document: TenderDocument) -> bool:
    """True when the stored document is a presupuesto key doc, not a misclassified pliego."""
    if document.document_type != "presupuesto":
        return False
    normalized = normalize_document_filename(document.file_name)
    if any(hint in normalized for hint in _PRESUPUESTO_FILENAME_REJECT):
        return False
    return True


def _score_document(document: TenderDocument, hints: tuple[str, ...]) -> int:
    normalized = normalize_document_filename(document.file_name)
    score = document.file_size or 0
    for index, hint in enumerate(hints):
        if hint in normalized:
            score += 10_000 - (index * 100)
    return score


def select_pliego_document(documents: list[TenderDocument]) -> Optional[TenderDocument]:
    candidates = [doc for doc in documents if doc.document_type == "pliego_condiciones"]
    if not candidates:
        return None
    pdf_candidates = [doc for doc in candidates if (doc.extension or "").lower() == "pdf"]
    pool = pdf_candidates or candidates
    return max(pool, key=lambda doc: _score_document(doc, _PLIEGO_HINTS))


def select_presupuesto_document(documents: list[TenderDocument]) -> Optional[TenderDocument]:
    candidates = [doc for doc in documents if doc.document_type == "presupuesto"]
    if not candidates:
        return None
    validated = [doc for doc in candidates if is_presupuesto_source_document(doc)]
    pool = validated or candidates
    return max(pool, key=lambda doc: _score_document(doc, _PRESUPUESTO_HINTS))
