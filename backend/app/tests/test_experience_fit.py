from datetime import date

from app.services.experience_fit import (
    NO_APLICA,
    NO_SE_PUEDE_AFIRMAR,
    PUEDE_APLICAR,
    evaluate_experience_fit,
)
from app.services.general_experience import general_experience_is_saved
from app.services.object_match import parse_object_match_payload

_SMMLV_2026 = 1_423_500.0


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
    matched_ids = set(matched or [])
    payload = {
        "tender_kind": "interventoria",
        "tender_object": "Interventoría al mejoramiento de la vía en pavimento",
        "experiences": experiences,
        "matched_experience_ids": matched_ids,
        "comparison_available": available,
        "paragraph_matched_ids": tender.pop("paragraph_matched_ids", matched_ids),
        "paragraph_comparison_available": tender.pop("paragraph_available", True),
    }
    payload.update(tender)
    return evaluate_experience_fit(**payload)


def _general_requirements(**items):
    stored = {
        "min_percentage_budget": items.get("percentage", 100),
        "time_window_years": items.get("years"),
        "contracts_minimum": items.get("contracts"),
        "min_amount_smmlv": items.get("direct"),
    }
    return {
        "extraction_version": "general-1",
        "general_experience_extracted": True,
        "sections": [
            {
                "key": "experiencia_general",
                "items": [
                    {
                        "key": "requirement_description",
                        "value": "Experiencia general en interventoría de obras viales.",
                    },
                    *[
                        {"key": key, "value": value}
                        for key, value in stored.items()
                        if value is not None
                    ],
                ],
            },
            {
                "key": "experiencia_especifica",
                "items": [
                    {
                        "key": "specific_scope",
                        "value": items.get(
                            "specific",
                            "No aplica para el presente proceso.",
                        ),
                    }
                ],
            },
        ],
    }


def _budget_for(smmlv: float) -> float:
    return smmlv * _SMMLV_2026


def test_object_match_without_a_read_pliego_cannot_be_affirmed():
    result = _evaluate(
        [_contract(object_text="Interventoría de redes de acueducto")],
        matched=["exp-1232"],
        requirements=None,
    )
    assert result.status == NO_SE_PUEDE_AFIRMAR
    assert "pliego" in result.reason.lower()


def test_sum_below_the_pliego_minimum_does_not_apply():
    result = _evaluate(
        [_contract(amount_smmlv=222, completion_date=date(2024, 1, 10))],
        matched=["exp-1232"],
        requirements=_general_requirements(percentage=100),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_APLICA
    assert result.general_sum_smmlv == 222
    assert result.general_minimum_smmlv == 300


def test_sum_that_covers_the_minimum_can_apply():
    result = _evaluate(
        [
            _contract(amount_smmlv=150, completion_date=date(2024, 1, 10)),
            _contract(
                experience_id="exp-2",
                contract_number="0681 DE 2002",
                amount_smmlv=160,
                completion_date=date(2023, 5, 1),
            ),
        ],
        matched=["exp-1232", "exp-2"],
        requirements=_general_requirements(percentage=100),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == PUEDE_APLICAR
    assert result.general_sum_smmlv == 310
    assert result.general_minimum_smmlv == 300


def test_a_contract_outside_the_date_window_stays_out_of_the_sum():
    result = _evaluate(
        [
            _contract(amount_smmlv=400, completion_date=date(2010, 1, 1)),
            _contract(
                experience_id="exp-2",
                amount_smmlv=100,
                completion_date=date(2024, 1, 1),
            ),
        ],
        matched=["exp-1232", "exp-2"],
        requirements=_general_requirements(percentage=100, years=5),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_APLICA
    assert result.general_sum_smmlv == 100


def test_a_missing_date_inside_a_required_window_cannot_be_affirmed():
    result = _evaluate(
        [_contract(amount_smmlv=400, completion_date=None)],
        matched=["exp-1232"],
        requirements=_general_requirements(percentage=100, years=5),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_SE_PUEDE_AFIRMAR


def test_without_a_window_an_old_contract_still_counts():
    result = _evaluate(
        [_contract(amount_smmlv=400, completion_date=date(1990, 1, 1))],
        matched=["exp-1232"],
        requirements=_general_requirements(percentage=100),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == PUEDE_APLICAR
    assert result.general_sum_smmlv == 400


def test_contract_count_uses_the_largest_contracts_that_fit_the_range():
    result = _evaluate(
        [
            _contract(amount_smmlv=200),
            _contract(experience_id="exp-2", amount_smmlv=180),
        ],
        matched=["exp-1232", "exp-2"],
        requirements=_general_requirements(
            percentage=100,
            contracts={"minimum": 1, "maximum": 1},
        ),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_APLICA
    assert result.general_sum_smmlv == 200


def test_salary_copied_into_the_smmlv_column_stays_out_of_the_sum():
    result = _evaluate(
        [_contract(amount_smmlv=81510)],
        matched=["exp-1232"],
        requirements=_general_requirements(direct=100),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_APLICA
    assert result.general_sum_smmlv == 0


def test_a_full_requirements_extract_counts_as_already_read():
    assert general_experience_is_saved(
        {
            "extraction_version": "1.9.11",
            "sections": [{"key": "experiencia_general", "items": []}],
        }
    )
    assert not general_experience_is_saved(None)
    assert not general_experience_is_saved({"sections": []})


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


def test_an_acta_outside_the_pliego_experience_does_not_apply():
    result = _evaluate(
        [_contract(amount_smmlv=400, completion_date=date(2024, 1, 1))],
        matched=["exp-1232"],
        paragraph_matched_ids=set(),
        requirements=_general_requirements(
            percentage=100,
            specific="Interventoría de obras de drenaje asociadas a la infraestructura de transporte.",
        ),
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_APLICA
    assert "experiencia" in result.reason.lower()


def test_unread_specific_experience_cannot_be_affirmed():
    requirements = _general_requirements(percentage=100)
    requirements["sections"] = [
        section
        for section in requirements["sections"]
        if section["key"] == "experiencia_general"
    ]
    result = _evaluate(
        [_contract(amount_smmlv=400, completion_date=date(2024, 1, 1))],
        matched=["exp-1232"],
        requirements=requirements,
        tender_amount=_budget_for(300),
        publication_date=date(2026, 6, 1),
    )
    assert result.status == NO_SE_PUEDE_AFIRMAR
    assert "específica" in result.reason.lower()


def test_experience_paragraph_keeps_only_actas_that_already_matched():
    from unittest.mock import patch

    from app.services.object_match import _CACHE, judge_object_matches

    _CACHE.clear()
    tenders = [
        {
            "id": "tender::general",
            "kind": "interventoria",
            "object": "Experiencia en interventoría de obras de drenaje.",
            "candidate_ids": ["exp-drenaje"],
        }
    ]
    experiences = [
        {
            "experience_id": "exp-drenaje",
            "contract_kind": "interventoria",
            "has_acta": True,
            "object_text": "Interventoría de obras de drenaje vial",
        },
        {
            "experience_id": "exp-via",
            "contract_kind": "interventoria",
            "has_acta": True,
            "object_text": "Interventoría de pavimento",
        },
    ]
    with patch(
        "app.services.object_match._call_openai",
        return_value={"tender::general": {"exp-drenaje", "exp-via"}},
    ) as called:
        matches, failed = judge_object_matches(
            tenders, experiences, client=object(), purpose="experience"
        )
    assert [row["experience_id"] for row in called.call_args.args[2]] == ["exp-drenaje"]
    assert called.call_args.args[3] == "experience"
    assert matches["tender::general"] == {"exp-drenaje"}
    assert failed == set()


def test_road_tender_does_not_match_a_sewer_acta_even_if_the_model_says_yes():
    from unittest.mock import patch

    from app.services.object_match import _CACHE, judge_object_matches

    _CACHE.clear()
    tenders = [
        {
            "id": "t-barrios-unidos",
            "kind": "ejecucion_obra",
            "object": (
                "OBRAS DE CONSERVACIÓN DE LA MALLA VIAL LOCAL E INTERMEDIA Y DEL "
                "ESPACIO PÚBLICO EN LA LOCALIDAD DE BARRIOS UNIDOS"
            ),
        }
    ]
    experiences = [
        {
            "experience_id": "exp-042",
            "contract_kind": "ejecucion_obra",
            "has_acta": True,
            "object_text": (
                "la construcción y la reparación de redes de alcantarillado "
                "localizadas en Kennedy y Bosa"
            ),
        }
    ]
    with patch(
        "app.services.object_match._call_openai",
        return_value={"t-barrios-unidos": {"exp-042"}},
    ):
        matches, failed = judge_object_matches(tenders, experiences, client=object())
    assert matches["t-barrios-unidos"] == set()
    assert failed == set()


def test_general_experience_smmlv_follows_its_percentage_of_the_budget():
    from app.services.experience_fit import present_general_experience_smmlv

    payload = {
        "sections": [
            {
                "key": "experiencia_general",
                "items": [
                    {"key": "min_percentage_budget", "value": 100, "source_document": "pliego_condiciones"},
                    {"key": "min_amount_smmlv", "value": 35.54, "display_value": "35.54 SMMLV"},
                ],
            }
        ]
    }

    shown = present_general_experience_smmlv(
        payload,
        tender_amount=56_138_545,
        publication_date=date(2026, 3, 1),
    )

    amount = shown["sections"][0]["items"][1]
    assert amount["value"] == round(56_138_545 / _SMMLV_2026, 2)
    assert amount["display_value"] == "39,44 SMMLV"
    assert amount["evidence"] == "100% del presupuesto oficial expresado en SMMLV"
    assert payload["sections"][0]["items"][1]["value"] == 35.54


def test_a_direct_smmlv_stays_when_general_experience_states_no_percentage():
    from app.services.experience_fit import present_general_experience_smmlv

    payload = {
        "sections": [
            {
                "key": "experiencia_general",
                "items": [{"key": "min_amount_smmlv", "value": 500, "display_value": "500 SMMLV"}],
            }
        ]
    }

    shown = present_general_experience_smmlv(
        payload,
        tender_amount=56_138_545,
        publication_date=date(2026, 3, 1),
    )

    assert shown["sections"][0]["items"][0]["value"] == 500


def test_same_road_specialty_keeps_the_model_match():
    from unittest.mock import patch

    from app.services.object_match import _CACHE, judge_object_matches

    _CACHE.clear()
    tenders = [
        {
            "id": "t-via",
            "kind": "ejecucion_obra",
            "object": "Conservación de la malla vial local",
        }
    ]
    experiences = [
        {
            "experience_id": "exp-via",
            "contract_kind": "ejecucion_obra",
            "has_acta": True,
            "object_text": "Mejoramiento vial y pavimentación de la vía urbana",
        }
    ]
    with patch(
        "app.services.object_match._call_openai",
        return_value={"t-via": {"exp-via"}},
    ):
        matches, failed = judge_object_matches(tenders, experiences, client=object())
    assert matches["t-via"] == {"exp-via"}
    assert failed == set()


def test_parser_keeps_only_ids_from_the_prompt():
    parsed = parse_object_match_payload(
        {"tenders": [{"tender_id": "t1", "experience_ids": ["exp-1", "invented"]}]},
        {"t1": {"exp-1"}},
    )
    assert parsed["t1"] == {"exp-1"}
