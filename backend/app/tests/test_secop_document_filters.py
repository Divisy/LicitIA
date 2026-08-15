"""Tests for SECOP document classification (user story 1.2)."""
from app.services.secop_document_filters import DocumentType, classify_document, is_key_document


def test_classify_pliego():
    assert classify_document("7-PLIEGO DE CONDICIONES DEFINITIVOS.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("Documento Base CCE proceso 2026.pdf") == DocumentType.PLIEGO_CONDICIONES


def test_classify_anexo_tecnico():
    assert classify_document("ANEXO TECNICO SDHT-LP-002-2026 .pdf") == DocumentType.ANEXO_TECNICO
    assert classify_document("Especificaciones técnicas obra.pdf") == DocumentType.ANEXO_TECNICO


def test_classify_presupuesto():
    assert classify_document("PRESUPUESTO SAN BERNARDO.pdf") == DocumentType.PRESUPUESTO
    assert classify_document("07_FORMATO OFERTA ECONOMICA PRESUPUESTO.xlsx") == DocumentType.PRESUPUESTO


def test_classify_otro():
    assert classify_document("Aviso de Convocatoria.pdf") == DocumentType.OTRO
    assert classify_document("CDP 2026.pdf") == DocumentType.OTRO


def test_is_key_document():
    assert is_key_document(DocumentType.PLIEGO_CONDICIONES) is True
    assert is_key_document(DocumentType.OTRO) is False
