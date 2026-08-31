"""Pick canonical pliego/anexo/indicadores documents for requirements extraction."""
from __future__ import annotations

from typing import Optional

from app.models.tender_document import TenderDocument
from app.services.secop_document_filters import normalize_document_filename
from app.services.tender_summary.document_selection import select_pliego_document

_ANEXO_HINTS = (
    "anexo tecnico",
    "anexo técnico",
    "anexo tec",
    "especificaciones tecnicas",
    "especificaciones técnicas",
    "documento tecnico",
    "documento técnico",
)

_INDICADORES_HINTS = (
    "matriz 2 - indicadores financieros",
    "matriz 2 indicadores",
    "indicadores financieros y organizacionales",
    "indicadores financieros",
    "matriz de indicadores",
    "solvencia economica",
    "formulario indicadores",
    "capacidad financiera y organizacional",
)


def _score_document(document: TenderDocument, hints: tuple[str, ...]) -> int:
    normalized = normalize_document_filename(document.file_name)
    score = document.file_size or 0
    for index, hint in enumerate(hints):
        if hint in normalized:
            score += 10_000 - (index * 100)
    return score


def select_anexo_document(documents: list[TenderDocument]) -> Optional[TenderDocument]:
    candidates = [doc for doc in documents if doc.document_type == "anexo_tecnico"]
    if not candidates:
        return None
    pdf_candidates = [doc for doc in candidates if (doc.extension or "").lower() == "pdf"]
    pool = pdf_candidates or candidates
    return max(pool, key=lambda doc: _score_document(doc, _ANEXO_HINTS))


def select_indicadores_financieros_document(
    documents: list[TenderDocument],
) -> Optional[TenderDocument]:
    candidates = [doc for doc in documents if doc.document_type == "indicadores_financieros"]
    if not candidates:
        return None
    pdf_candidates = [doc for doc in candidates if (doc.extension or "").lower() == "pdf"]
    pool = pdf_candidates or candidates
    return max(pool, key=lambda doc: _score_document(doc, _INDICADORES_HINTS))


__all__ = [
    "select_pliego_document",
    "select_anexo_document",
    "select_indicadores_financieros_document",
]
