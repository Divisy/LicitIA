from datetime import date
from decimal import Decimal
from pathlib import Path

from app.services.bec_experience_import import (
    COMPANY_NAME,
    parse_bec_experience_csv,
    parse_decimal,
)
from app.services.project_typology import apply_project_typologies

CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "bec_experiencia_socios.csv"


def test_parses_colombian_amounts():
    assert parse_decimal("$415.680.829,5") == Decimal("415680829.5")
    assert parse_decimal("1.219,00") == Decimal("1219.00")
    assert parse_decimal("50%") == Decimal("50")
    assert parse_decimal(" -   ") is None


def test_sheet_rows_belong_to_bec_and_keep_the_partner():
    rows, errors = parse_bec_experience_csv(CSV_PATH)
    assert errors == []
    assert rows

    beatriz = next(row for row in rows if row.contract_number == "1129-2009")
    assert beatriz.partner_code == "BEVB"
    assert beatriz.partner_name == "Beatriz"
    assert beatriz.start_date == date(2009, 1, 30)
    assert beatriz.completion_date == date(2009, 10, 26)
    assert beatriz.participation_percent == Decimal("50")
    assert beatriz.amount_smmlv == Decimal("418.00")
    assert beatriz.amount == Decimal("595023000.0")
    assert "Vivienda" in (beatriz.specific_experience or "")

    otto = next(
        row
        for row in rows
        if row.partner_code == "OHG" and row.contract_number == "1232 DE 2006"
    )
    assert otto.partner_name == "Otto Harry"
    assert otto.contracting_entity == "INVIAS"
    assert otto.participation_percent == Decimal("100")

    partners = {row.partner_name for row in rows}
    assert partners == {"Otto Harry", "Beatriz"}
    assert all(row.import_key for row in rows)
    assert len({row.import_key for row in rows}) == len(rows)


def test_short_specific_tag_keeps_the_contract_typology():
    class Experience:
        specific_experience = "Puentes"
        project_description = (
            "Mantenimiento estructural y actualización sísmica de puentes peatonales en Bogotá"
        )
        project_typologies = None

    assert "puentes" in apply_project_typologies(Experience())


def test_company_constant_is_bec():
    assert COMPANY_NAME == "BEC"
