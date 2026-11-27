"""The experience chapter is cut the same way for tipo and non-tipo pliegos."""
from app.services.experience_section import (
    amount_is_project_band,
    experience_section_excerpt,
    labeled_specific_scope,
    reconcile_general_fields,
    reconcile_specific_fields,
)


TIPO = """
Entre 1.001 y 23.000 SMMLV por la complejidad del proyecto de la localidad.
EXPERIENCIA GENERAL: construcción de vías urbanas.
NOTA 2: experiencia en vías únicamente urbanas.
NOTA 4: no se acepta experiencia cuya ejecución sea exclusivamente en afirmado.
EXPERIENCIA ESPECÍFICA: por lo menos uno de los contratos debe acreditar la intervención
de la estructura de pavimento y la intervención de redes de servicios públicos.
El proponente podrá acreditar la experiencia con mínimo uno (1) y máximo cinco (5) contratos.
3.5.9 Valor mínimo a certificar (como % del Presupuesto Oficial de obra expresado en SMMLV)
De 1 hasta 2 75 %
De 3 hasta 4 120 %
Hasta 5 150 %
3.6 Capacidad financiera. Liquidez y endeudamiento.
"""

NON_TIPO = """
3.1 EXPERIENCIA GENERAL
El proponente deberá acreditar experiencia general en interventoría de obras,
equivalente al treinta por ciento (30%) del presupuesto oficial, en los últimos 5 años.
3.2 SOLVENCIA ECONOMICA Y FINANCIERA
El índice de liquidez deberá ser mayor o igual a 1.0.
"""


def test_the_table_of_contents_is_not_the_chapter():
    text = (
        "3.5 Requisitos minimos de experiencia ................................ 27\n"
        "3.6 Capacidad financiera ............................................. 37\n"
        + TIPO
    )
    excerpt = experience_section_excerpt(text)
    assert "pavimento" in excerpt.lower()
    assert "75" in excerpt
    assert "Liquidez" not in excerpt


def test_tipo_chapter_keeps_the_value_table_and_stops_before_finance():
    excerpt = experience_section_excerpt(TIPO)
    assert "únicamente urbanas" in excerpt
    assert "pavimento" in excerpt
    assert "75" in excerpt
    assert "Liquidez" not in excerpt


def test_non_tipo_chapter_stops_at_solvencia():
    excerpt = experience_section_excerpt(NON_TIPO)
    assert "treinta por ciento" in excerpt
    assert "liquidez" not in excerpt.lower()


def test_a_long_chapter_still_includes_the_value_table():
    filler = "condiciones de presentación de la oferta. " * 400
    text = (
        "EXPERIENCIA GENERAL: construcción de vías urbanas. "
        + filler
        + "Valor mínimo a certificar. De 1 hasta 2 75 %. De 3 hasta 4 120 %. Hasta 5 150 %. "
        + "Capacidad financiera."
    )
    excerpt = experience_section_excerpt(text)
    assert "75" in excerpt
    assert "construcción de vías urbanas" in excerpt


def test_project_band_is_not_kept_when_the_chapter_has_a_value_table():
    fields = reconcile_general_fields(
        {"requirement_description": "construcción de vías urbanas", "min_amount_smmlv": 1001},
        TIPO,
    )
    assert fields["experience_value_tiers"][0] == {"contract_range": "1-2", "percentage": 75.0}
    assert "min_amount_smmlv" not in fields
    assert fields["contracts_minimum"] == {"minimum": 1, "maximum": 5}
    assert amount_is_project_band(TIPO, 1001)


def test_specific_scope_uses_the_labeled_block_instead_of_the_activity():
    fields = reconcile_specific_fields(
        {"specific_scope": "PROYECTOS DE CONSTRUCCIÓN DE VÍAS URBANAS. 6.1 proyectos de vías urbanas."},
        TIPO,
    )
    assert "pavimento" in fields["specific_scope"].lower()
    assert labeled_specific_scope(NON_TIPO) is None
