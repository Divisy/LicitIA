"""Tests for LLM enrichment of tender requirements (US 1.5)."""
from unittest.mock import MagicMock, patch

from app.services.tender_requirements.llm_extraction import enrich_requirements_with_llm


def _llm_response(sections: dict) -> MagicMock:
    message = MagicMock()
    message.content = '{"sections": ' + __import__("json").dumps(sections) + "}"
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_skipped_when_disabled(mock_settings):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = False
    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="Experiencia general del 30%",
        existing_sections=existing,
    )
    assert result == existing


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_refines_sections_when_regex_already_filled(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "requirement_description",
                    "label": "Descripción del requisito",
                    "display_value": (
                        "Interventoría de proyectos de construcción, rehabilitación o "
                        "conservación de vías."
                    ),
                    "evidence": "interventoria a proyectos de construccion",
                    "confidence": 0.91,
                }
            ],
            "experiencia_especifica": [
                {
                    "key": "specific_scope",
                    "label": "Alcance exigido",
                    "display_value": (
                        "Al menos un contrato de experiencia general debe equivaler al "
                        "60% del Presupuesto Oficial."
                    ),
                    "evidence": "por lo menos el 60% del valor del presupuesto oficial",
                    "confidence": 0.89,
                }
            ],
        }
    )

    existing = {
        "experiencia_general": [
            {
                "key": "requirement_description",
                "label": "Descripción del requisito",
                "display_value": "interventoria a proyectos de construccion o mejoramiento...",
                "confidence": 0.92,
                "extraction_method": "regex",
            }
        ],
        "experiencia_especifica": [
            {
                "key": "specific_scope",
                "label": "Alcance exigido",
                "display_value": "por lo menos uno (1) de los contratos validos...",
                "confidence": 0.92,
                "extraction_method": "regex",
            }
        ],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="3.1 EXPERIENCIA GENERAL ... 60% del presupuesto oficial",
        existing_sections=existing,
    )

    assert result["experiencia_general"][0]["extraction_method"] == "llm"
    assert "Interventoría" in result["experiencia_general"][0]["display_value"]
    assert result["experiencia_especifica"][0]["extraction_method"] == "llm"
    mock_client.chat.completions.create.assert_called_once()


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_fills_sparse_experience_sections(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "min_percentage_budget",
                    "label": "Experiencia mínima",
                    "display_value": "30% del PO",
                    "evidence": "treinta por ciento (30%) del presupuesto oficial",
                    "confidence": 0.88,
                }
            ],
            "experiencia_especifica": [
                {
                    "key": "specific_min_percentage",
                    "label": "Experiencia específica",
                    "display_value": "20% del PO",
                    "evidence": "equivalente al 20% del valor del contrato",
                    "confidence": 0.82,
                }
            ],
        }
    )

    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="3.1 EXPERIENCIA GENERAL ... 30% ... 4. EXPERIENCIA ESPECIFICA 20%",
        existing_sections=existing,
    )

    assert len(result["experiencia_general"]) == 1
    assert result["experiencia_general"][0]["extraction_method"] == "llm"
    assert len(result["experiencia_especifica"]) == 1
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["response_format"] == {"type": "json_object"}


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_keeps_regex_when_model_returns_nothing(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {"experiencia_general": [], "experiencia_especifica": []}
    )

    regex_item = {
        "key": "min_percentage_budget",
        "label": "Porcentaje",
        "display_value": "100%",
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    existing = {"experiencia_general": [regex_item], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )

    assert result["experiencia_general"] == [regex_item]


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_rejects_low_confidence_items(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "min_percentage_budget",
                    "label": "Experiencia mínima",
                    "display_value": "30%",
                    "evidence": "fragmento",
                    "confidence": 0.55,
                }
            ]
        }
    )

    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )

    assert result["experiencia_general"] == []


@patch("app.services.tender_requirements.llm_extraction._openai_client", None)
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_skipped_without_openai_client(mock_settings):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )
    assert result == existing
