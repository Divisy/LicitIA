"""Tests for anticipo extraction in tender summary (US 1.4)."""
from unittest.mock import MagicMock, patch

from app.services.tender_summary.llm_extraction import (
    extract_anticipo_with_llm,
    resolve_anticipo_extraction,
)
from app.services.tender_summary.pliego_extraction import extract_advance_payment_from_text
from app.services.tender_summary.text_selection import select_anticipo_text_for_llm


def test_extract_advance_payment_detects_no_anticipo():
    text = (
        "8.3 ANTICIPO Y/O PAGO ANTICIPADO. "
        "En el presente proceso la entidad no entregará al contratista anticipo y/o pago anticipado."
    )
    assert extract_advance_payment_from_text(text) == 0.0


def test_extract_advance_payment_detects_percentage():
    text = "Se otorgará un anticipo del 20% del valor del contrato."
    assert extract_advance_payment_from_text(text) == 20.0


def test_select_anticipo_text_finds_section_without_full_pliego():
    long_prefix = "INTRODUCCION " * 500
    anticipo_section = (
        "8.3 ANTICIPO Y/O PAGO ANTICIPADO. "
        "En el presente proceso la entidad no entregará al contratista anticipo y/o pago anticipado."
    )
    full_text = long_prefix + anticipo_section
    excerpt = select_anticipo_text_for_llm(None, full_text, max_chars=4_000)
    assert "no entregará al contratista anticipo" in excerpt
    assert len(excerpt) < len(full_text)


def test_resolve_anticipo_uses_regex_on_focused_excerpt():
    excerpt = (
        "8.3 ANTICIPO. La entidad no entregará al contratista anticipo y/o pago anticipado."
    )
    result = resolve_anticipo_extraction(
        tender_external_id="CO1.REQ.TEST",
        object_text="Obra vial",
        excerpt=excerpt,
        fallback_text="",
    )
    assert result is not None
    assert result.percentage == 0.0
    assert result.extraction_method == "regex"
    assert "Sin anticipo" in result.display_value


def _llm_response(payload: dict) -> MagicMock:
    import json

    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@patch("app.services.tender_summary.llm_extraction._openai_client")
@patch("app.services.tender_summary.llm_extraction.settings")
def test_extract_anticipo_with_llm(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_USE_LLM_FOR_ANTICIPO = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_SUMMARY_ANTICIPO_LLM_MAX_CHARS = 6000
    mock_settings.TENDER_SUMMARY_ANTICIPO_LLM_MIN_CONFIDENCE = 0.70
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "advance_payment_percentage": 30,
            "display_value": "30% del valor del contrato",
            "confidence": 0.92,
            "evidence": "anticipo del treinta por ciento",
        }
    )

    result = extract_anticipo_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Construcción de vía",
        context_excerpt="El anticipo será del 30% del valor estimado del contrato.",
    )
    assert result is not None
    assert result.percentage == 30.0
    assert result.extraction_method == "llm"
