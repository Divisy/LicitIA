from app.services.experience_fit import (
    NO_APLICA,
    NO_SE_PUEDE_AFIRMAR,
    PUEDE_APLICAR,
    evaluate_experience_fit,
)
from app.services.object_match import parse_object_match_payload


def _contract(**overrides) -> dict:
    row = {
        "experience_id": "exp-1232",
        "contract_number": "1232 DE 2006",
        "contracting_entity": "INVIAS",
        "contract_kind": "interventoria",
        "object_text": "Interventoría para el mejoramiento de la vía Las Margaritas-Cauya",
        "partidas": "",
        "amount_smmlv": 222,
        "has_acta": True,
    }
    row.update(overrides)
    return row


def _evaluate(experiences, matched=None, available=True, **tender):
    payload = {
        "tender_kind": "interventoria",
        "tender_object": "Interventoría al mejoramiento de la vía en pavimento",
        "experiences": experiences,
        "matched_experience_ids": set(matched or []),
        "comparison_available": available,
    }
    payload.update(tender)
    return evaluate_experience_fit(**payload)


def test_same_kind_and_openai_match_can_apply_without_typology_or_pliego():
    result = _evaluate(
        [_contract(object_text="Interventoría de redes de acueducto")],
        matched=["exp-1232"],
        requirements=None,
    )
    assert result.status == PUEDE_APLICAR
    assert result.contracts[0].experience_id == "exp-1232"


def test_same_kind_without_object_match_does_not_apply():
    result = _evaluate([_contract()], matched=[])
    assert result.status == NO_APLICA
    assert result.contracts == []


def test_a_different_contract_kind_is_not_compared():
    result = _evaluate(
        [_contract(contract_kind="ejecucion_obra")],
        matched=["exp-1232"],
    )
    assert result.status == NO_SE_PUEDE_AFIRMAR
    assert "acta" in result.reason.lower()


def test_missing_acta_object_cannot_be_affirmed():
    result = _evaluate([_contract(has_acta=False)])
    assert result.status == NO_SE_PUEDE_AFIRMAR


def test_openai_failure_cannot_be_affirmed():
    result = _evaluate([_contract()], available=False)
    assert result.status == NO_SE_PUEDE_AFIRMAR
    assert "comparar" in result.reason.lower()


def test_parser_keeps_only_ids_from_the_prompt():
    parsed = parse_object_match_payload(
        {"tenders": [{"tender_id": "t1", "experience_ids": ["exp-1", "invented"]}]},
        {"t1": {"exp-1"}},
    )
    assert parsed["t1"] == {"exp-1"}
