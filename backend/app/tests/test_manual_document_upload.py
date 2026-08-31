"""Tests for manual tender document upload."""
import pytest

from app.services.manual_document_upload import (
    validate_document_type,
    validate_upload_filename,
)
from app.services.secop_document_filters import DocumentType


def test_validate_document_type_accepts_key_types():
    assert validate_document_type("presupuesto") == DocumentType.PRESUPUESTO
    assert validate_document_type("pliego_condiciones") == DocumentType.PLIEGO_CONDICIONES
    assert validate_document_type("anexo_tecnico") == DocumentType.ANEXO_TECNICO
    assert validate_document_type("indicadores_financieros") == DocumentType.INDICADORES_FINANCIEROS


def test_validate_document_type_rejects_unknown():
    with pytest.raises(ValueError):
        validate_document_type("cdp")


def test_validate_upload_filename():
    assert validate_upload_filename("Presupuesto Oficial.xlsx") == "Presupuesto Oficial.xlsx"
    assert (
        validate_upload_filename(
            "Matriz 2.docx",
            DocumentType.INDICADORES_FINANCIEROS,
        )
        == "Matriz 2.docx"
    )
    with pytest.raises(ValueError):
        validate_upload_filename("archivo.zip")
    with pytest.raises(ValueError):
        validate_upload_filename("matriz.docx")
