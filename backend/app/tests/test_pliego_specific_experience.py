"""The pliego's specific experience is copied from the printed page."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.pliego_specific_experience import (
    apply_focused_specific_experience_section,
    finish_specific_reading,
    specific_experience_reading_is_final,
)
from app.services.tender_requirements.llm_extraction import (
    extract_specific_experience_from_page_images,
    parse_specific_experience_llm_payload,
)


def test_parser_copies_the_specific_section_and_drops_a_salary_figure():
    parsed = parse_specific_experience_llm_payload(
        {
            "specific_scope": (
                "El proponente deberá acreditar experiencia específica mediante un (1) contrato "
                "de interventoría a estudios y diseños de edificaciones de interés cultural."
            ),
            "specific_min_percentage": 100,
            "min_amount_smmlv": 35.54,
            "contracts_minimum": {"minimum": 1, "maximum": 1},
        }
    )

    assert parsed["specific_scope"].startswith("El proponente deberá acreditar")
    assert parsed["specific_min_percentage"] == 100
    assert parsed["min_amount_smmlv"] == 35.54
    assert parsed["contracts_minimum"] == {"minimum": 1, "maximum": 1}

    rejected = parse_specific_experience_llm_payload({"min_amount_smmlv": 81510, "specific_scope": "corto"})
    assert rejected == {}


def test_a_text_extract_is_replaced_by_the_printed_specific_page():
    payload = {
        "extraction_version": "1.9.11",
        "sections": [
            {"key": "experiencia_general", "items": [{"key": "min_percentage_budget", "value": 100}]},
            {"key": "experiencia_especifica", "items": [{"key": "specific_scope", "value": "lectura por reglas"}]},
        ],
    }
    focused = {
        "key": "experiencia_especifica",
        "title": "Experiencia específica",
        "status": "extraido",
        "items": [{"key": "specific_scope", "value": "uno (1) contrato de interventoría patrimonial"}],
    }

    updated = apply_focused_specific_experience_section(payload, focused, "pages")

    assert updated["sections"][0]["key"] == "experiencia_general"
    assert updated["sections"][1]["items"][0]["value"].startswith("uno (1)")
    assert updated["specific_experience_source"] == "pages"
    assert specific_experience_reading_is_final(updated)
    assert not specific_experience_reading_is_final(payload)


@patch("app.services.pliego_specific_experience.extract_specific_experience_from_page_images")
@patch("app.services.pliego_specific_experience._render_specific_experience_pages", return_value=[b"page"])
def test_the_specific_section_is_read_from_its_printed_page(_pages, mock_vision):
    mock_vision.return_value = {
        "specific_scope": "Experiencia específica habilitante: un (1) contrato de interventoría patrimonial.",
        "specific_min_percentage": 100,
        "min_amount_smmlv": 35.54,
    }
    pliego = SimpleNamespace(id=uuid4())

    payload = finish_specific_reading(pliego, "CO1.REQ.1", {"sections": []})

    assert mock_vision.call_args.kwargs["page_images"] == [b"page"]
    assert payload["specific_experience_source"] == "pages"
    assert payload["sections"][0]["items"][0]["value"].startswith("Experiencia específica")
    assert payload["sections"][0]["items"][2]["value"] == 35.54


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_the_specific_page_image_goes_to_the_model(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    message = MagicMock()
    message.content = '{"specific_scope":"un (1) contrato de interventoría a estudios y diseños patrimoniales"}'
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])

    parsed = extract_specific_experience_from_page_images(
        tender_external_id="CO1.REQ.1",
        page_images=[b"one", b"two", b"three"],
    )

    content = mock_client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    images = [part for part in content if part["type"] == "image_url"]
    assert len(images) == 3
    assert images[0]["image_url"]["detail"] == "high"
    assert parsed["specific_scope"].startswith("un (1) contrato")


def test_a_contract_count_is_not_the_specific_experience_paragraph():
    count_only = {
        "specific_experience_llm": True,
        "specific_experience_source": "pages",
        "sections": [
            {
                "key": "experiencia_especifica",
                "items": [
                    {
                        "key": "specific_scope",
                        "value": (
                            "Se aceptará la acreditación mediante un contrato o la sumatoria "
                            "de hasta dos contratos."
                        ),
                    }
                ],
            }
        ],
    }
    assert not specific_experience_reading_is_final(count_only)

    with_activity = {
        "specific_experience_llm": True,
        "specific_experience_source": "pages",
        "sections": [
            {
                "key": "experiencia_especifica",
                "items": [
                    {
                        "key": "specific_scope",
                        "value": "Construcción y/o ampliación y/o reconstrucción de edificaciones.",
                    }
                ],
            }
        ],
    }
    assert specific_experience_reading_is_final(with_activity)
