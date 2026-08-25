"""Tests for tender requirements extraction (US 1.5)."""
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.tender_requirements.regex_extraction import (
    extract_experiencia_especifica,
    extract_experiencia_general,
    extract_indicadores_financieros,
    extract_otros_requisitos,
    extract_requisitos_legales,
    normalize_text,
)
from app.services.tender_requirements.service import build_tender_requirements


PLIEGO_SAMPLE = """
CAPITULO III REQUISITOS DE PARTICIPACION
3.1 EXPERIENCIA GENERAL
El proponente deberá acreditar experiencia general equivalente al treinta por ciento (30%)
del presupuesto oficial de la presente licitación, ejecutada en los últimos 5 años.
La experiencia se acreditará mediante Matriz 1 y certificados de experiencia.

3.2 SOLVENCIA ECONOMICA Y FINANCIERA
El índice de liquidez corriente deberá ser mayor o igual a 1.0.
La calificación por solvencia tendrá un puntaje de 20 puntos.

3.3 REQUISITOS LEGALES
El proponente deberá estar inscrito en el Registro Único de Proponentes (RUP) con capacidad jurídica.
Deberá contar con licencia de construcción vigente cuando aplique.
"""

ANEXO_SAMPLE = """
ANEXO TECNICO
4. EXPERIENCIA ESPECIFICA
El proponente deberá demostrar experiencia específica en interventoría de obras viales,
equivalente al 20% del valor del contrato.
Códigos de actividad UNSPSC: 72141100, 72141200
"""


def test_normalize_text_strips_accents():
    assert normalize_text("Últimos 5 años") == "ultimos 5 anos"


def test_extract_experiencia_general_percentage_and_years():
    items = extract_experiencia_general(PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "min_percentage_budget" in keys
    assert "time_window_years" in keys
    pct = next(item for item in items if item["key"] == "min_percentage_budget")
    assert pct["value"] == 30


def test_extract_experiencia_general_accreditation():
    items = extract_experiencia_general(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "accreditation_method" for item in items)


def test_extract_experiencia_especifica_scope_and_codes():
    items = extract_experiencia_especifica(ANEXO_SAMPLE, "anexo_tecnico", None)
    keys = {item["key"] for item in items}
    assert "specific_scope" in keys
    assert "activity_codes" in keys
    codes = next(item for item in items if item["key"] == "activity_codes")
    assert "72141100" in codes["value"]


def test_extract_indicadores_financieros_liquidez():
    items = extract_indicadores_financieros(PLIEGO_SAMPLE, "pliego_condiciones", None)
    liquidez = next((item for item in items if item["key"] == "liquidez_corriente"), None)
    assert liquidez is not None
    assert liquidez["value"]["threshold"] == 1.0


def test_extract_indicadores_financieros_puntaje():
    items = extract_indicadores_financieros(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "qualification_score" for item in items)


def test_extract_requisitos_legales_rup():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "rup_vigente" in keys
    assert "legal_capacity" in keys


def test_extract_requisitos_legales_license():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "specific_license" for item in items)


def test_extract_otros_requisitos_pyme():
    text = "Se dará prioridad a empresas MiPyme y emprendimiento de mujer."
    items = extract_otros_requisitos(text, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "pyme" in keys
    assert "mujer" in keys


def test_build_tender_requirements_without_documents():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Obra vial",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    assert payload["sections"]
    assert all(
        section["status"] == "documento_no_disponible"
        for section in payload["sections"]
        if section["key"] != "otros"
    )


def test_build_tender_requirements_section_keys():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST2",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Obra vial",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    section_keys = [section["key"] for section in payload["sections"]]
    assert section_keys == [
        "experiencia_general",
        "experiencia_especifica",
        "indicadores_financieros",
        "requisitos_legales",
        "otros",
    ]
