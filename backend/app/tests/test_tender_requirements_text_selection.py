"""Tests for requirement text selection (US 1.5)."""
from app.services.tender_requirements.regex_extraction import extract_experiencia_especifica, extract_experiencia_general
from app.services.tender_requirements.text_selection import select_requirement_relevant_text

_EXPERIENCE_SECTION = """
3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
contratos aportados como experiencia es mayor o igual al cien por ciento (100 %) respecto del valor
total del Presupuesto Oficial establecido para el Proceso de Contratacion expresado en SMMLV.

De conformidad con lo anterior, los requisitos de experiencia son:
• EXPERIENCIA GENERAL : INTERVENTORIA A LA CONSTRUCCION O RECONSTRUCCION
O MEJORAMIENTO EN PAVIMENTO ASFALTICO O CONCRETO HIDRAULICO DE VIAS PRIMARIAS
• EXPERIENCIA ESPECIFICA: Por lo menos uno (1) de los contratos validos aportados como
experiencia general sea de un valor correspondiente a por lo menos el 70% del valor de
PRESUPUESTO OFICIAL (PO) del presente proceso de contratacion.
"""


def test_select_requirement_relevant_text_keeps_experience_section():
    filler = "introduccion y definiciones. " * 8_000
    raw = filler + _EXPERIENCE_SECTION
    selected = select_requirement_relevant_text(raw, max_chars=80_000)

    general = extract_experiencia_general(selected, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(selected, "pliego_condiciones", None)

    general_keys = {item["key"] for item in general}
    specific_keys = {item["key"] for item in specific}

    assert "requirement_description" in general_keys
    assert "min_percentage_budget" in general_keys
    assert "specific_scope" in specific_keys
    assert "specific_min_percentage" in specific_keys
