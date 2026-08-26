"""Tests for pliego TOC navigation (US 1.5)."""
from app.services.tender_requirements.regex_extraction import (
    extract_experiencia_especifica,
    extract_experiencia_general,
)
from app.services.tender_requirements.text_selection import prepare_pliego_requirement_text
from app.services.tender_requirements.toc_parser import locate_pages_from_toc, parse_toc_entries

INDEX_SAMPLE = """
3.8 EXIGENCIAS MINIMAS DE LA EXPERIENCIA DEL PROPONENTE .......................... 32
3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE .......................... 32
4.1 FORMA DE VERIFICACION Y ASIGNACION DE PUNTAJE POR LA EXPERIENCIA ............ 55
10.1 ACREDITACION DE LA EXPERIENCIA DEL PROPONENTE ............................... 76
3.5 SOLVENCIA ECONOMICA Y FINANCIERA ............................................. 28
3.4 CAPACIDAD JURIDICA ........................................................... 25
"""

BODY_PAGES = {
    30: "introduccion general del proceso",
    31: "continuacion de definiciones",
    32: """
3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
contratos aportados como experiencia es mayor o igual al cien por ciento (100 %)
respecto del valor total del Presupuesto Oficial expresado en SMMLV.
De conformidad con lo anterior, los requisitos de experiencia son:
• EXPERIENCIA GENERAL : INTERVENTORIA A LA CONSTRUCCION O RECONSTRUCCION
• EXPERIENCIA ESPECIFICA: Por lo menos uno (1) de los contratos validos aportados como
experiencia general sea de un valor correspondiente a por lo menos el 70% del valor de
PRESUPUESTO OFICIAL (PO) del presente proceso de contratacion.
""",
    33: "condiciones adicionales de experiencia y formatos",
}


def test_parse_toc_entries_finds_experience_section():
    entries = parse_toc_entries(INDEX_SAMPLE)
    pages = [(1, INDEX_SAMPLE), (32, BODY_PAGES[32])]
    located = locate_pages_from_toc(pages)
    assert entries
    assert located.get("experiencia")
    assert 32 in located["experiencia"]


def test_prepare_pliego_text_from_toc_pages():
    pages = [(page_no, text) for page_no, text in BODY_PAGES.items()]
    pages.insert(0, (1, INDEX_SAMPLE))
    selected, notes = prepare_pliego_requirement_text(pages, "\n".join(t for _, t in pages), 50_000)

    general = extract_experiencia_general(selected, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(selected, "pliego_condiciones", None)

    assert notes
    assert any(item["key"] == "requirement_description" for item in general)
    assert any(item["key"] == "specific_min_percentage" for item in specific)
