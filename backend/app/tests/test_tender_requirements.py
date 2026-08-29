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


CCE_PLIEGO_EXPERIENCE = """
3.5 EXPERIENCIA
De conformidad con lo anterior, los requisitos de experiencia son: 2.2 MEJORAMIENTO EN VIAS TERCIARIAS.
EXPERIENCIA GENERAL: CONSTRUCCION O RECONSTRUCCION O MEJORAMIENTO EN PLACA HUELLA DE VIAS TERCIARIAS.
El Proponente podra acreditar la experiencia solicitada con minimo uno (1) y maximo cinco (5) contratos.
3.5.9 RELACION DE LOS CONTRATOS FRENTE AL PRESUPUESTO OFICIAL
De 1 hasta 2 75%
De 3 hasta 4 120%
150% Hasta 5
Numero de contratos con los cuales el Proponente cumple la experiencia acreditada
Valor minimo a certificar (como % del Presupuesto Oficial de obra expresado en SMMLV)
La verificacion se hara con base en la sumatoria de los valores totales ejecutados en SMMLV.
"""


def test_extract_cce_experience_value_tiers_and_contracts():
    general = extract_experiencia_general(CCE_PLIEGO_EXPERIENCE, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(CCE_PLIEGO_EXPERIENCE, "pliego_condiciones", None)
    general_keys = {item["key"] for item in general}
    specific_keys = {item["key"] for item in specific}

    assert "experience_value_tiers" in general_keys
    assert "contracts_minimum" in general_keys
    assert "min_amount_smmlv" in general_keys
    assert "experience_value_tiers" not in specific_keys

    tiers = next(item for item in general if item["key"] == "experience_value_tiers")
    assert tiers["value"] == [
        {"contract_range": "1-2", "percentage": 75.0},
        {"contract_range": "3-4", "percentage": 120.0},
        {"contract_range": "1-5", "percentage": 150.0},
    ]


def test_interventoria_experience_does_not_use_contract_tier_table():
    text = """
    3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
    contratos aportados como experiencia es mayor o igual al cien por ciento (100 %)
    respecto del valor total del Presupuesto Oficial expresado en SMMLV.
    EXPERIENCIA GENERAL: INTERVENTORIA DE OBRAS VIALES.
    EXPERIENCIA ESPECIFICA: al menos el 60% del Presupuesto Oficial del presente proceso.
    """
    general = extract_experiencia_general(text, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(text, "pliego_condiciones", None)
    assert "experience_value_tiers" not in {item["key"] for item in general}
    assert "experience_value_tiers" not in {item["key"] for item in specific}
    assert "min_percentage_budget" in {item["key"] for item in general}
    assert "specific_min_percentage" in {item["key"] for item in specific}


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


INVIAS_PLIEGO_SAMPLE = """
3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
contratos aportados como experiencia es mayor o igual al cien por ciento (100 %) respecto del valor
total del Presupuesto Oficial establecido para el Proceso de Contratacion expresado en SMMLV.
Formato 3 - Experiencia y Matriz 1 - Experiencia.

De conformidad con lo anterior, los requisitos de experiencia son:
• EXPERIENCIA GENERAL : INTERVENTORIA A LA CONSTRUCCION O RECONSTRUCCION
O MEJORAMIENTO EN PAVIMENTO ASFALTICO O CONCRETO HIDRAULICO DE VIAS PRIMARIAS
• EXPERIENCIA ESPECIFICA: Por lo menos uno (1) de los contratos validos aportados como
experiencia general sea de un valor correspondiente a por lo menos el 70% del valor de
PRESUPUESTO OFICIAL (PO) del presente proceso de contratacion.
"""


def test_invias_pliego_extracts_general_and_specific_experience():
    general = extract_experiencia_general(INVIAS_PLIEGO_SAMPLE, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(INVIAS_PLIEGO_SAMPLE, "pliego_condiciones", None)

    general_keys = {item["key"] for item in general}
    assert "requirement_description" in general_keys
    assert "min_percentage_budget" in general_keys
    assert any(item["value"] == 100 for item in general if item["key"] == "min_percentage_budget")

    specific_keys = {item["key"] for item in specific}
    assert "specific_scope" in specific_keys
    assert "specific_min_percentage" in specific_keys
    assert any(item["value"] == 70 for item in specific if item["key"] == "specific_min_percentage")


def test_extract_otros_requisitos_pyme():
    text = "El Proponente podra acreditar la calidad de Mipyme y de emprendimiento y empresa de mujeres."
    items = extract_otros_requisitos(text, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "pyme" in keys
    assert "mujer" in keys
    assert "mocho" not in keys


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
