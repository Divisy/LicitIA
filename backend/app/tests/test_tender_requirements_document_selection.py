"""Tests for indicadores financieros document selection."""
from uuid import uuid4

from app.models.tender_document import TenderDocument
from app.services.tender_requirements.document_selection import (
    select_indicadores_financieros_document,
)


def _doc(file_name: str, document_type: str, file_size: int = 1000) -> TenderDocument:
    return TenderDocument(
        id=uuid4(),
        tender_id=uuid4(),
        external_document_id=f"secop-{uuid4().hex[:8]}",
        file_name=file_name,
        document_type=document_type,
        extension=file_name.rsplit(".", 1)[-1],
        file_size=file_size,
    )


def test_select_indicadores_financieros_prefers_matriz_over_generic_pdf():
    generic = _doc("indicadores.pdf", "indicadores_financieros", 500)
    matriz = _doc(
        "Matriz 2 - Indicadores Financieros y Organizacionales.pdf",
        "indicadores_financieros",
        400,
    )
    selected = select_indicadores_financieros_document([generic, matriz])
    assert selected is not None
    assert "Matriz 2" in selected.file_name


def test_select_indicadores_financieros_prefers_matriz_docx_over_formato_pdf():
    formato = _doc(
        "Formato 4- capacidad financiera y organizacional interventoria V3.pdf",
        "indicadores_financieros",
        60_000,
    )
    matriz = _doc(
        "Matriz 2 - Indicadores Financieros y Organizacionales v3.docx",
        "indicadores_financieros",
        800_000,
    )
    selected = select_indicadores_financieros_document([formato, matriz])
    assert selected is not None
    assert "Matriz 2" in selected.file_name


def test_select_indicadores_financieros_skips_formato_template():
    formato = _doc(
        "Formato 4- capacidad financiera y organizacional interventoria V3.pdf",
        "indicadores_financieros",
        60_000,
    )
    assert select_indicadores_financieros_document([formato]) is None


def test_select_indicadores_financieros_finds_matriz_stored_as_otro():
    matriz = _doc(
        "Matriz 2 - Indicadores Financieros y Organizacionales v3.docx",
        "otro",
        800_000,
    )
    selected = select_indicadores_financieros_document([matriz])
    assert selected is not None
    assert "Matriz 2" in selected.file_name


def test_select_indicadores_financieros_returns_none_when_missing():
    pliego = _doc("Pliego.pdf", "pliego_condiciones")
    assert select_indicadores_financieros_document([pliego]) is None
