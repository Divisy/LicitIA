"""US 2.7: one AI read of the pliego's general experience."""
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.experience_fit import PUEDE_APLICAR, evaluate_experience_fit
from types import SimpleNamespace

from app.services.general_experience import (
    GENERAL_EXPERIENCE_LLM_VERSION,
    GENERAL_EXPERIENCE_VERSION,
    _job_lock,
    extract_general_experience_batch,
    finish_focused_reading,
    general_experience_excerpt,
    general_experience_items_from_fields,
    general_experience_llm_is_saved,
    general_experience_reading_is_final,
    payload_for_general_experience_reading,
    _printed_page_span,
)
from app.services.tender_requirements.llm_extraction import (
    extract_general_experience_from_page_images,
    extract_general_experience_with_llm,
    parse_general_experience_llm_payload,
)

_SMMLV_2026 = 1_423_500.0


def _model_payload() -> dict:
    return {
        "requirement_description": (
            "El proponente debe acreditar experiencia general en interventoría de obras viales."
        ),
        "min_percentage_budget": "100%",
        "min_amount_smmlv": "smmlv",
        "time_window_years": 5,
        "contracts_minimum": {"minimum": 1, "maximum": 3},
        "experience_value_tiers": None,
        "evidence": {
            "requirement_description": "experiencia general en interventoria de obras viales",
            "min_percentage_budget": "100% del presupuesto oficial",
            "time_window_years": "ultimos 5 anos",
            "contracts_minimum": "minimo 1 y maximo 3 contratos",
        },
    }


def test_parser_keeps_written_numbers_and_drops_empty_ones():
    parsed = parse_general_experience_llm_payload(_model_payload())

    assert parsed["min_percentage_budget"] == 100
    assert parsed["time_window_years"] == 5
    assert "company_duration" not in parsed
    assert parsed["contracts_minimum"] == {"minimum": 1, "maximum": 3}
    assert "min_amount_smmlv" not in parsed
    assert "experience_value_tiers" not in parsed


def test_parser_keeps_company_life_out_of_the_experience_window():
    parsed = parse_general_experience_llm_payload(
        {
            "time_window_years": 5,
            "company_duration": (
                "El término de duración de la persona jurídica no podrá ser inferior "
                "al plazo de ejecución del contrato, su liquidación y cinco (5) años más."
            ),
            "evidence": {
                "time_window_years": "liquidación y cinco (5) años más",
            },
        }
    )

    assert "time_window_years" not in parsed
    assert "persona jurídica" in parsed["company_duration"]
    assert "cinco (5) años más" in parsed["company_duration"]


def test_parser_rejects_a_salary_copied_as_smmlv_and_a_missing_percentage():
    parsed = parse_general_experience_llm_payload(
        {
            "min_percentage_budget": None,
            "min_amount_smmlv": 81510,
            "time_window_years": "últimos años",
            "contracts_minimum": {"minimum": "varios", "maximum": 1},
        }
    )

    assert parsed == {}


def test_parser_reads_tiers_written_as_ranges():
    parsed = parse_general_experience_llm_payload(
        {
            "experience_value_tiers": [
                {"contract_range": "de 1 hasta 2", "percentage": 100},
                {"contract_range": "3-6", "percentage": 80},
            ]
        }
    )

    assert parsed["experience_value_tiers"] == [
        {"contract_range": "1-2", "percentage": 100},
        {"contract_range": "3-6", "percentage": 80},
    ]


def test_ai_numbers_are_what_the_smmlv_match_reads():
    fields = parse_general_experience_llm_payload(_model_payload())
    items = general_experience_items_from_fields(fields, uuid4())
    result = evaluate_experience_fit(
        tender_kind="interventoria",
        tender_object="Interventoría al mejoramiento de la vía",
        experiences=[
            {
                "experience_id": "exp-1",
                "contract_number": "1",
                "contracting_entity": "INVIAS",
                "contract_kind": "interventoria",
                "object_text": "Interventoría vial",
                "amount_smmlv": 400,
                "has_acta": True,
                "completion_date": date(2024, 1, 1),
            }
        ],
        matched_experience_ids={"exp-1"},
        comparison_available=True,
        paragraph_matched_ids={"exp-1"},
        paragraph_comparison_available=True,
        tender_amount=300 * _SMMLV_2026,
        publication_date=date(2026, 6, 1),
        requirements={
            "extraction_version": GENERAL_EXPERIENCE_LLM_VERSION,
            "general_experience_extracted": True,
            "general_experience_llm": True,
            "sections": [
                {"key": "experiencia_general", "items": items},
                {
                    "key": "experiencia_especifica",
                    "items": [
                        {
                            "key": "specific_scope",
                            "value": "No aplica para el presente proceso.",
                        }
                    ],
                },
            ],
        },
    )

    assert result.status == PUEDE_APLICAR
    assert result.general_minimum_smmlv == 300
    assert items[0]["extraction_method"] == "llm"


def test_a_full_extract_keeps_the_focused_general_experience_section():
    from app.services.general_experience import apply_focused_general_experience_section

    regex_row = {
        "extraction_version": GENERAL_EXPERIENCE_VERSION,
        "general_experience_extracted": True,
        "sections": [{"key": "experiencia_general", "items": [{"key": "min_percentage_budget"}]}],
    }
    full_extract = {
        "extraction_version": "1.9.11",
        "sections": [
            {"key": "indicadores_financieros", "items": [{"key": "liquidez_corriente"}]},
            {
                "key": "experiencia_general",
                "items": [
                    {
                        "key": "requirement_description",
                        "value": "párrafo de la lectura completa",
                        "extraction_method": "llm",
                    }
                ],
                "status": "revisar",
            },
        ],
    }
    focused = {
        "key": "experiencia_general",
        "title": "Experiencia general",
        "status": "extraido",
        "items": [{"key": "min_percentage_budget", "value": 100, "extraction_method": "llm"}],
    }

    assert not general_experience_llm_is_saved(regex_row)
    assert not general_experience_llm_is_saved(full_extract)
    patched = apply_focused_general_experience_section(full_extract, focused)
    assert general_experience_llm_is_saved(patched)
    assert patched["extraction_version"] == "1.9.11"
    assert patched["sections"][0]["key"] == "indicadores_financieros"
    assert patched["sections"][1]["items"][0]["value"] == 100
    assert general_experience_llm_is_saved({"general_experience_llm": True, "sections": []})


def test_a_failed_call_keeps_the_regex_read():
    existing = {
        "extraction_version": GENERAL_EXPERIENCE_VERSION,
        "general_experience_extracted": True,
        "sections": [{"key": "experiencia_general", "items": [{"key": "min_percentage_budget", "value": 100}]}],
    }

    assert (
        payload_for_general_experience_reading(
            existing,
            tender_external_id="CO1.REQ.1",
            text="experiencia general del 100% del presupuesto oficial",
            llm_fields=None,
            source_document_id=uuid4(),
        )
        is None
    )


def test_a_failed_call_without_a_previous_read_stores_regex_for_a_later_retry():
    payload = payload_for_general_experience_reading(
        None,
        tender_external_id="CO1.REQ.1",
        text="experiencia general: interventoria de vias en los ultimos 5 anos",
        llm_fields=None,
        source_document_id=uuid4(),
    )

    assert payload["extraction_version"] == GENERAL_EXPERIENCE_VERSION
    assert "general_experience_llm" not in payload


def test_a_successful_call_replaces_regex_and_a_full_extract_keeps_its_other_sections():
    fields = parse_general_experience_llm_payload(_model_payload())
    partial = payload_for_general_experience_reading(
        {
            "extraction_version": GENERAL_EXPERIENCE_VERSION,
            "general_experience_extracted": True,
            "sections": [{"key": "experiencia_general", "items": [{"key": "min_percentage_budget", "value": 50}]}],
        },
        tender_external_id="CO1.REQ.1",
        text="experiencia general",
        llm_fields=fields,
        source_document_id=uuid4(),
    )
    full = payload_for_general_experience_reading(
        {
            "extraction_version": "1.9.11",
            "sections": [
                {"key": "indicadores_financieros", "items": [{"key": "liquidez_corriente"}]},
                {"key": "experiencia_general", "items": [{"key": "min_percentage_budget", "value": 50}]},
            ],
        },
        tender_external_id="CO1.REQ.1",
        text="experiencia general",
        llm_fields=fields,
        source_document_id=uuid4(),
    )

    assert partial["extraction_version"] == GENERAL_EXPERIENCE_LLM_VERSION
    assert partial["general_experience_llm"] is True
    assert partial["sections"][0]["items"][1]["value"] == 100
    assert full["extraction_version"] == "1.9.11"
    assert full["sections"][0]["key"] == "indicadores_financieros"
    assert full["general_experience_llm"] is True


def test_a_pliego_without_text_is_not_sent_to_the_model():
    payload = payload_for_general_experience_reading(
        None,
        tender_external_id="CO1.REQ.1",
        text="  ",
        llm_fields={"min_percentage_budget": 100},
        source_document_id=uuid4(),
    )

    assert payload["general_experience_llm"] is True
    assert payload["sections"][0]["items"] == []
    assert "No se pudo leer texto del pliego" in payload["warnings"]


def test_excerpt_stays_inside_the_model_cap():
    text = "portada " * 1000 + " experiencia general " + ("requisito de interventoria vial " * 2000)
    excerpt = general_experience_excerpt(text)

    assert len(excerpt) <= 8000
    assert "experiencia general" in excerpt


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_the_call_uses_only_the_general_experience_excerpt(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    message = MagicMock()
    message.content = (
        '{"requirement_description": "Experiencia general en interventoria de vias.", '
        '"min_percentage_budget": 100, "min_amount_smmlv": null, '
        '"time_window_years": null, "contracts_minimum": null, "experience_value_tiers": null}'
    )
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create.return_value = response

    parsed = extract_general_experience_with_llm(
        tender_external_id="CO1.REQ.1",
        excerpt="experiencia general: 100% del presupuesto oficial",
    )

    sent = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "experiencia general: 100% del presupuesto oficial" in sent
    assert "indicadores" not in sent.lower() or "Ignora experiencia específica, indicadores" in sent
    assert parsed["min_percentage_budget"] == 100
    assert "min_amount_smmlv" not in parsed
    assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-mini"


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_three_printed_pages_go_to_the_model(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    message = MagicMock()
    message.content = '{"requirement_description":"uno (1) o hasta dos (2) contratos","contracts_minimum":{"minimum":1,"maximum":2}}'
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=message)]
    )

    parsed = extract_general_experience_from_page_images(
        tender_external_id="CO1.REQ.1",
        page_images=[b"one", b"two", b"three", b"four"],
    )

    content = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    images = [part for part in content if part["type"] == "image_url"]
    assert len(images) == 3
    assert images[0]["image_url"]["detail"] == "high"
    assert parsed["contracts_minimum"] == {"minimum": 1, "maximum": 2}


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_a_failed_model_call_returns_nothing_to_store(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.side_effect = TimeoutError("openai down")

    assert (
        extract_general_experience_with_llm(
            tender_external_id="CO1.REQ.1",
            excerpt="experiencia general",
        )
        is None
    )


def test_a_text_reading_is_replaced_by_the_printed_pages():
    assert not general_experience_reading_is_final({"general_experience_llm": True, "sections": []})
    assert not general_experience_reading_is_final(
        {"general_experience_llm": True, "general_experience_source": "text", "sections": []}
    )
    assert not general_experience_reading_is_final(
        {"general_experience_llm": True, "general_experience_source": "pages", "sections": []}
    )
    assert not general_experience_reading_is_final(
        {
            "general_experience_llm": True,
            "general_experience_source": "pages",
            "sections": [
                {
                    "key": "experiencia_general",
                    "items": [
                        {
                            "key": "requirement_description",
                            "value": (
                                "Se deberá presentar un (1) contrato adicional a los cinco (5) "
                                "inicialmente previstos, para un máximo de seis (6) contratos."
                            ),
                        }
                    ],
                }
            ],
        }
    )
    assert general_experience_reading_is_final(
        {
            "general_experience_llm": True,
            "general_experience_source": "pages",
            "sections": [
                {
                    "key": "experiencia_general",
                    "items": [
                        {
                            "key": "requirement_description",
                            "value": (
                                "Proyectos de construcción y/o ampliación y/o reconstrucción de edificaciones."
                            ),
                        }
                    ],
                }
            ],
        }
    )
    assert general_experience_reading_is_final(
        {"general_experience_llm": True, "general_experience_source": "vision", "sections": []}
    )
    assert not general_experience_reading_is_final(
        {
            "general_experience_llm": True,
            "general_experience_source": "vision",
            "sections": [
                {"key": "experiencia_general", "items": [{"key": "time_window_years", "value": 5}]}
            ],
        }
    )
    assert general_experience_reading_is_final(
        {"general_experience_llm": True, "general_experience_source": "no_pages", "sections": []}
    )


def test_the_page_before_the_heading_is_included():
    assert list(_printed_page_span(25, 78, 3)) == [24, 25, 26]
    assert list(_printed_page_span(0, 78, 3)) == [0, 1, 2]


@patch("app.services.general_experience.extract_general_experience_with_llm")
@patch("app.services.general_experience.extract_general_experience_from_page_images")
@patch("app.services.general_experience._render_general_experience_pages", return_value=[b"a", b"b", b"c"])
@patch(
    "app.services.general_experience._read_pliego_text",
    return_value="experiencia general habilitante: uno (1) o hasta dos (2) contratos",
)
def test_every_pliego_is_read_from_three_printed_pages(_text, _pages, mock_vision, mock_text_llm):
    mock_vision.return_value = {
        "requirement_description": "uno (1) o hasta dos (2) contratos de interventoría",
        "contracts_minimum": {"minimum": 1, "maximum": 2},
    }
    pliego = SimpleNamespace(id=uuid4())

    payload = finish_focused_reading(pliego, "CO1.REQ.1", {"general_experience_llm": True, "sections": []})

    mock_vision.assert_called_once()
    assert mock_vision.call_args.kwargs["page_images"] == [b"a", b"b", b"c"]
    mock_text_llm.assert_not_called()
    assert payload["general_experience_source"] == "pages"
    description = payload["sections"][0]["items"][0]["value"]
    assert description.startswith("uno (1) o hasta dos (2)")


@patch("app.services.general_experience.extract_general_experience_from_page_images", return_value=None)
@patch("app.services.general_experience._render_general_experience_pages", return_value=[b"a"])
@patch("app.services.general_experience._read_pliego_text", return_value="")
def test_a_failed_page_reading_is_retried(_text, _pages, _vision):
    pliego = SimpleNamespace(id=uuid4())
    existing = {"general_experience_llm": True, "sections": []}

    assert finish_focused_reading(pliego, "CO1.REQ.1", existing) is None


def test_a_running_drain_makes_the_batch_wait_for_the_next_pass():
    assert _job_lock.acquire(blocking=False)
    try:
        assert extract_general_experience_batch(MagicMock()) == 0
    finally:
        _job_lock.release()
