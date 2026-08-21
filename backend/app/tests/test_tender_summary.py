"""Tests for US 1.4 tender summary extraction."""
from datetime import datetime
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.tender_summary.contract_kind import ContractKind, detect_contract_kind
from app.services.tender_summary.pliego_extraction import extract_from_pliego_text
from app.services.tender_summary.service import build_tender_summary


def _tender(**kwargs) -> Tender:
    defaults = {
        "id": uuid4(),
        "external_id": "CO1.REQ.TEST",
        "portfolio_id": "portfolio-1",
        "source": TenderSource.SECOP_II,
        "entity_name": "Entidad prueba",
        "object_text": "Interventoria de la malla vial municipal",
        "state": "Publicado",
        "process_url": "https://example.com",
        "department": "Cundinamarca",
        "municipality": "Bogotá",
        "amount": 830309008,
        "closing_date": datetime(2026, 8, 18),
        "contract_type": "Interventoria",
        "contract_modality": "Licitacion publica",
        "documents": [],
    }
    defaults.update(kwargs)
    return Tender(**defaults)


def test_detect_contract_kind_interventoria():
    tender = _tender(object_text="Contrato de interventoria de obra vial")
    assert detect_contract_kind(tender) == ContractKind.INTERVENTORIA


def test_detect_contract_kind_ejecucion_obra():
    tender = _tender(
        object_text="Construccion y mejoramiento de vias urbanas",
        contract_type="Obra",
    )
    assert detect_contract_kind(tender) == ContractKind.EJECUCION_OBRA


def test_extract_pliego_fields_from_text():
    text = """
    PLIEGO DE CONDICIONES
    Plazo de ejecucion del contrato: 8 meses
    Anticipo del 20% del valor del contrato
    Forma de pago: pagos parciales mensuales contra actas
    Ajuste de precios mediante formula polinomica
    El proceso se divide en 2 lotes
    """
    result = extract_from_pliego_text(text)
    assert result.execution_duration == "8 meses"
    assert result.advance_payment_percentage == 20.0
    assert "pagos parciales" in (result.payment_method or "").lower()
    assert result.price_adjustment == "Sí"
    assert result.lots_groups == "Sí"


def test_extract_plazo_from_table_with_spanish_words():
    text = """
    PRESUPUESTO OFICIAL, PLAZO Y UBICACION
    Plazo del contrato
    MEJORAMIENTO VIAL DEL ACCESO BARRIO LA CARPA
    DOS MESES Y QUINCE DIAS
    MIL CUATROCIENTOS DIECINUEVE MILLONES
    """
    result = extract_from_pliego_text(text)
    assert result.execution_duration == "2 meses y 15 días"


def test_extract_plazo_until_date():
    text = """
    PLAZO Y UBICACION
    Plazo del contrato HASTA 31 DE DICIEMBRE DE 2026
    """
    result = extract_from_pliego_text(text)
    assert result.execution_duration == "Hasta 31 de Diciembre de 2026"


def test_extract_pliego_from_real_local_pdf():
    from pathlib import Path

    from pypdf import PdfReader

    pdf = Path(
        "storage/documents/CO1.REQ.10533907/pliego_condiciones/"
        "811207733_Documento Base - Licitacion - Cucuta Pto Sder - Proyecto de Pliego.pdf"
    )
    if not pdf.is_file():
        return

    reader = PdfReader(str(pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:35])
    result = extract_from_pliego_text(text)
    assert result.execution_duration == "Hasta 31 de Diciembre de 2026"


def test_build_summary_marks_aiu_not_applicable_for_interventoria():
    tender = _tender()
    summary = build_tender_summary(tender)
    aiu = next(field for field in summary["fields"] if field["key"] == "aiu_percentage")
    assert aiu["status"] == "not_applicable"
    assert summary["contract_kind"] == "interventoria"


def test_build_summary_includes_secop_fields():
    tender = _tender()
    summary = build_tender_summary(tender)
    keys = {field["key"] for field in summary["fields"]}
    assert "offer_submission_date" in keys
    assert "work_description" in keys
    assert "admin_location" in keys
    assert "total_cost" in keys
    assert "monthly_cost" in keys
