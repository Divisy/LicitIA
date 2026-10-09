from datetime import date

from app.services.acta_partidas import extract_acta_partidas_from_text
from app.services.experience_fit import (
    NO_APLICA,
    NO_SE_PUEDE_AFIRMAR,
    PUEDE_APLICAR,
    evaluate_experience_fit,
)
from app.services.rup_parser import _SMMLV_BY_YEAR

WAGE = _SMMLV_BY_YEAR[2026]
BUDGET = 300 * WAGE


def _requirements(scope: str, years: int | None = None) -> dict:
    general = [
        {"key": "min_percentage_budget", "value": 100},
        {"key": "specific_scope", "value": scope},
    ]
    specific = [
        {"key": "specific_scope", "value": scope},
        {"key": "specific_min_percentage", "value": 70},
    ]
    if years is not None:
        general.append({"key": "time_window_years", "value": years})
    return {
        "sections": [
            {"key": "experiencia_general", "items": general},
            {"key": "experiencia_especifica", "items": specific},
        ]
    }


def _contract(**overrides) -> dict:
    row = {
        "experience_id": "exp-1232",
        "contract_number": "1232 DE 2006",
        "contracting_entity": "INVIAS",
        "contract_kind": "interventoria",
        "object_text": "Interventoría para el mejoramiento de la vía Las Margaritas-Cauya",
        "partidas": "Item 1 excavacion 120 m3. Item 2 base granular 80 m3.",
        "amount_smmlv": 222,
        "completion_date": date(2007, 2, 10),
        "has_acta": True,
    }
    row.update(overrides)
    return row


def _evaluate(experiences, **tender):
    payload = {
        "tender_kind": "interventoria",
        "tender_object": "Interventoría al mejoramiento de la vía en pavimento",
        "tender_amount": BUDGET,
        "publication_date": date(2026, 3, 1),
        "requirements": _requirements("pavimento asfáltico o concreto hidráulico"),
        "experiences": experiences,
    }
    payload.update(tender)
    return evaluate_experience_fit(**payload)


def test_partidas_are_kept_apart_from_the_object():
    text = """
    Objeto del contrato: interventoría para el mejoramiento de la vía.
    Partidas de obra
    Item 1 Carpeta asfáltica 1.200 m2
    Item 2 Concreto hidráulico 80 m3
    En constancia firman las partes.
    """
    partidas = extract_acta_partidas_from_text(
        text,
        objeto="interventoría para el mejoramiento de la vía",
    )
    assert partidas
    assert "carpeta asfaltica" in partidas.lower() or "Carpeta asfáltica" in partidas
    assert "interventoría para el mejoramiento de la vía" not in partidas.lower()


def test_sum_short_and_partidas_without_the_activity_do_not_apply():
    result = _evaluate([_contract()])
    assert result.status == NO_APLICA
    assert result.general_sum_smmlv == 222
    assert result.contracts[0].specific_met is False


def test_activity_in_the_object_does_not_accredit_specific_experience():
    result = _evaluate(
        [
            _contract(
                object_text="Interventoría de pavimento asfáltico en la vía Las Margaritas",
                partidas="Item 1 afirmado 50 m3. Item 2 cuneta 20 ml.",
            )
        ]
    )
    assert result.contracts[0].specific_met is False
    assert result.status == NO_APLICA


def test_asphalt_synonym_in_partidas_still_fails_when_the_sum_is_short():
    result = _evaluate(
        [_contract(partidas="Item 1 carpeta asfáltica 1.200 m2")]
    )
    assert result.contracts[0].specific_met is True
    assert result.status == NO_APLICA
    assert "general" in result.reason.lower()


def test_both_steps_pass_when_the_sum_and_the_partidas_cover_the_pliego():
    result = _evaluate(
        [
            _contract(partidas="Item 1 carpeta asfáltica 1.200 m2"),
            _contract(
                experience_id="exp-2",
                contract_number="229 DE 2014",
                amount_smmlv=80,
                partidas="Item 1 base granular 40 m3",
                completion_date=date(2014, 5, 1),
            ),
        ]
    )
    assert result.status == PUEDE_APLICAR
    assert result.general_sum_smmlv == 302
    assert any(row.specific_met for row in result.contracts)


def test_or_accepts_one_activity_and_and_requires_both():
    one = _evaluate(
        [_contract(partidas="Item 1 concreto hidráulico 30 m3", amount_smmlv=400)]
    )
    assert one.contracts[0].specific_met is True

    both = _evaluate(
        [_contract(partidas="Item 1 concreto hidráulico 30 m3", amount_smmlv=400)],
        requirements=_requirements("pavimento asfáltico y concreto hidráulico"),
    )
    assert both.contracts[0].specific_met is False


def test_missing_partidas_cannot_be_affirmed():
    result = _evaluate([_contract(partidas="")])
    assert result.status == NO_SE_PUEDE_AFIRMAR
    assert "partidas" in result.reason.lower()


def test_missing_pliego_cannot_be_affirmed():
    result = _evaluate([_contract()], requirements=None)
    assert result.status == NO_SE_PUEDE_AFIRMAR


def test_date_window_excludes_old_contracts_and_is_ignored_when_absent():
    outside = _evaluate(
        [_contract(partidas="Item 1 carpeta asfáltica 10 m2", amount_smmlv=400)],
        requirements=_requirements("pavimento asfáltico o concreto hidráulico", years=10),
    )
    assert outside.status == NO_APLICA
    assert outside.general_sum_smmlv == 0

    recent = _evaluate(
        [
            _contract(
                partidas="Item 1 carpeta asfáltica 10 m2",
                amount_smmlv=400,
                completion_date=date(2020, 1, 1),
            )
        ],
        requirements=_requirements("pavimento asfáltico o concreto hidráulico", years=10),
    )
    assert recent.status == PUEDE_APLICAR


def test_a_different_contract_kind_does_not_enter_the_sum():
    result = _evaluate(
        [
            _contract(
                contract_kind="ejecucion_obra",
                partidas="Item 1 carpeta asfáltica 10 m2",
                amount_smmlv=400,
            )
        ]
    )
    assert result.status == NO_APLICA
    assert result.contracts == []
