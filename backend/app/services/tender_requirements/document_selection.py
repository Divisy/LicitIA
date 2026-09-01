"""Pick canonical pliego/anexo/indicadores documents for requirements extraction."""
from __future__ import annotations

from typing import Optional

from app.models.tender_document import TenderDocument
from app.services.secop_document_filters import (
    is_indicadores_form_template_filename,
    normalize_document_filename,
)
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
    "matriz de indicadores",
    "indicadores financieros",
    "solvencia economica",
    "formulario indicadores",
)


def _score_document(document: TenderDocument, hints: tuple[str, ...]) -> int:
    normalized = normalize_document_filename(document.file_name)
    score = document.file_size or 0
    for index, hint in enumerate(hints):
        if hint in normalized:
            score += 10_000 - (index * 100)
    return score


def _is_matriz_indicadores_filename(document: TenderDocument) -> bool:
    normalized = normalize_document_filename(document.file_name)
    return "matriz 2" in normalized and "indicadores" in normalized


def _indicadores_candidates(documents: list[TenderDocument]) -> list[TenderDocument]:
    typed = [
        doc
        for doc in documents
        if doc.document_type == "indicadores_financieros"
        and not is_indicadores_form_template_filename(doc.file_name, doc.description)
    ]
    if typed:
        return typed

    return [
        doc
        for doc in documents
        if _is_matriz_indicadores_filename(doc)
        and not is_indicadores_form_template_filename(doc.file_name, doc.description)
    ]


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
    candidates = _indicadores_candidates(documents)
    if not candidates:
        return None

    matriz_candidates = [doc for doc in candidates if _is_matriz_indicadores_filename(doc)]
    pool = matriz_candidates or candidates
    return max(pool, key=lambda doc: _score_document(doc, _INDICADORES_HINTS))


__all__ = [
    "select_pliego_document",
    "select_anexo_document",
    "select_indicadores_financieros_document",
]
