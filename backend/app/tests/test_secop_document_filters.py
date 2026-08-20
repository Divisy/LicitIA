"""Tests for SECOP document classification (user stories 1.2 and 1.2.3)."""
from app.services.secop_document_filters import DocumentType, classify_document, is_key_document


def test_classify_pliego():
    assert classify_document("7-PLIEGO DE CONDICIONES DEFINITIVOS.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("Documento Base CCE proceso 2026.pdf") == DocumentType.PLIEGO_CONDICIONES


def test_classify_pliego_expanded_keywords():
    assert classify_document("5. PROYECTO DE PLIEGOS.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("PROYECTO PLIEGO LP-001-2026.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("PREPLIEGO DEFINITIVO.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("PLIEGO DEFINITIVO.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("6. Pliegos Definitivos  LP-005-2026.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("PC-MT-LP-003-2026-PROYECTO DE-PLIEGO.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("6. PLIEGO BASE - LP 116.pdf") == DocumentType.PLIEGO_CONDICIONES


def test_classify_anexo_tecnico():
    assert classify_document("ANEXO TECNICO SDHT-LP-002-2026 .pdf") == DocumentType.ANEXO_TECNICO
    assert classify_document("Especificaciones técnicas obra.pdf") == DocumentType.ANEXO_TECNICO


def test_classify_anexo_tecnico_expanded_keywords():
    assert classify_document("ANEXOS DE PROYECTO.pdf") == DocumentType.ANEXO_TECNICO
    assert classify_document("6. ANALISIS DEL SECTOR LP 08-2026.pdf") == DocumentType.ANEXO_TECNICO
    assert classify_document(
        "ESPECIFICACIONES TECNICAS GENERALES -CIVIL PALMIRA.pdf"
    ) == DocumentType.ANEXO_TECNICO


def test_classify_presupuesto():
    assert classify_document("PRESUPUESTO SAN BERNARDO.pdf") == DocumentType.PRESUPUESTO
    assert classify_document("07_FORMATO OFERTA ECONOMICA PRESUPUESTO.xlsx") == DocumentType.PRESUPUESTO


def test_classify_presupuesto_expanded_keywords():
    assert classify_document("1.2. PRESUPUESTO.rar") == DocumentType.PRESUPUESTO
    assert classify_document(
        "26. CCE-EICP-FM-14 Formul1 Presupuesto Oficial V4 30-07-2024.xlsx"
    ) == DocumentType.PRESUPUESTO
    assert classify_document("PPTO OFICIAL OBRA.pdf") == DocumentType.PRESUPUESTO
    assert classify_document("15_APU Ppto_Segovia.xlsx") == DocumentType.PRESUPUESTO
    assert classify_document("Formulario 1 - Economico Sumapaz V3.xlsx") == DocumentType.PRESUPUESTO
    assert classify_document("22. Formulario 1 - Propuesta economica CM-005-2026.xlsx") == DocumentType.PRESUPUESTO


def test_classify_presupuesto_formulario_1_does_not_false_positive():
    assert classify_document("ANÁLISIS ECONÓMICO DEL SECTOR CALLE LA L.pdf") == DocumentType.OTRO
    assert classify_document("Estudio del Sector Obra Sumapaz.pdf") == DocumentType.ANEXO_TECNICO


def test_classify_real_world_cases():
    assert classify_document("PROYECTO PLIEGO DE CONDICIONES LP 08-2026.pdf") == DocumentType.PLIEGO_CONDICIONES
    assert classify_document("ANEXO TECNICO LP 08-2026.pdf") == DocumentType.ANEXO_TECNICO
    assert classify_document("AVISO DE CONVOCATORIA.pdf") == DocumentType.OTRO


def test_classify_otro():
    assert classify_document("Aviso de Convocatoria.pdf") == DocumentType.OTRO
    assert classify_document("CDP 2026.pdf") == DocumentType.OTRO
    assert classify_document("1. ESTUDIO PREVIO.pdf") == DocumentType.OTRO


def test_is_key_document():
    assert is_key_document(DocumentType.PLIEGO_CONDICIONES) is True
    assert is_key_document(DocumentType.OTRO) is False
