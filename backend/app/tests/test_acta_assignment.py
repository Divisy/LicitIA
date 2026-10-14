from types import SimpleNamespace

from app.services.acta_assignment import (
    extract_contract_number_from_filename,
    extract_contract_number_from_text,
    match_contract_rows,
    same_contract,
)


def _row(number: str):
    return SimpleNamespace(contract_number=number)


def test_certificate_sentence_matches_the_rup_number():
    text = (
        "Contrato de Obra Pública No. 031 de 1.990, en la adecuación y "
        "construcción de canchas, valor de $ 9.970.530."
    )
    found = extract_contract_number_from_text(text)
    assert found is not None
    assert same_contract("031 de 1990", found)
    result = match_contract_rows(
        [_row("031 de 1990"), _row("537 de 1990")],
        found,
    )
    assert result.status == "assigned"
    assert result.rows[0].contract_number == "031 de 1990"


def test_a_different_contract_from_the_same_year_does_not_match():
    assert same_contract("537 de 1990", "031 de 1990") is False


def test_filename_number_matches_the_rup_row():
    found = extract_contract_number_from_filename(
        "11. IDRD Contrato 031 de 1990.pdf"
    )
    assert same_contract("031 de 1990", found or "")
    result = match_contract_rows([_row("1232 DE 2006")], "1232 de 2006")
    assert result.status == "assigned"


def test_short_number_does_not_swallow_a_longer_code():
    assert same_contract("042/87-DMALS", "042") is False
    assert same_contract("042/87-DMALS", "042/87-DMALS") is True


def test_same_number_in_two_partner_rows_is_one_assignment():
    result = match_contract_rows(
        [_row("1232 DE 2006"), _row("1232 DE 2006")],
        "Contrato No. 1232 de 2006",
    )
    assert result.status == "assigned"
    assert len(result.rows) == 2


def test_same_number_in_two_years_is_ambiguous_without_a_year():
    result = match_contract_rows(
        [_row("1232 DE 2006"), _row("1232 DE 2010")],
        "1232",
    )
    assert result.status == "ambiguous"


def test_year_picks_one_contract_when_the_number_repeats():
    result = match_contract_rows(
        [_row("1232 DE 2006"), _row("1232 DE 2010")],
        "1232 de 2006",
    )
    assert result.status == "assigned"
    assert result.rows[0].contract_number == "1232 DE 2006"
