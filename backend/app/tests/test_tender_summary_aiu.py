"""Tests for AIU extraction from presupuesto (US 1.4)."""
from unittest.mock import MagicMock, patch

from app.services.tender_summary.llm_extraction import (
    extract_aiu_with_llm,
    resolve_aiu_extraction,
)
from app.services.tender_summary.presupuesto_extraction import (
    extract_aiu_percentage_from_text,
    format_aiu_display,
)
from app.services.tender_summary.text_selection import select_aiu_text_for_llm

_SAMPLE_PRESUPUESTO_TAIL = """
PORCENTAJE
A= 24%
I= 1%
U= 5%
A.I.U.= 30%
VALOR UNITARIO
Formulario 1 - Propuesta económica
"""


def test_extract_aiu_from_presupuesto_text_direct_total():
    parsed = extract_aiu_percentage_from_text(_SAMPLE_PRESUPUESTO_TAIL)
    assert parsed.aiu_percentage == 30.0
    assert parsed.aiu_admin_percentage == 24.0
    assert parsed.aiu_imprevistos_percentage == 1.0
    assert parsed.aiu_utilidad_percentage == 5.0
    assert "30.00%" in format_aiu_display(parsed)
    assert "A 24%" in format_aiu_display(parsed)


def test_select_aiu_text_finds_tail_without_full_document():
    long_prefix = "ITEM DE OBRA " * 800
    full_text = long_prefix + _SAMPLE_PRESUPUESTO_TAIL
    excerpt = select_aiu_text_for_llm(None, full_text, max_chars=4_000)
    assert "A.I.U.= 30%" in excerpt or "A= 24%" in excerpt
    assert len(excerpt) < len(full_text)


def test_resolve_aiu_uses_regex_on_focused_excerpt():
    excerpt = _SAMPLE_PRESUPUESTO_TAIL
    result = resolve_aiu_extraction(
        tender_external_id="CO1.REQ.TEST",
        object_text="Mejoramiento vial",
        excerpt=excerpt,
        fallback_text="",
    )
    assert result is not None
    assert result.percentage == 30.0
    assert result.extraction_method == "regex"


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
def test_extract_aiu_with_llm(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_USE_LLM_FOR_AIU = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_SUMMARY_AIU_LLM_MAX_CHARS = 8000
    mock_settings.TENDER_SUMMARY_AIU_LLM_MIN_CONFIDENCE = 0.70
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "aiu_percentage": 30,
            "admin_percentage": 24,
            "imprevistos_percentage": 1,
            "utilidad_percentage": 5,
            "display_value": "30% (A 24% · I 1% · U 5%)",
            "confidence": 0.95,
            "evidence": "A.I.U.= 30%",
        }
    )

    result = extract_aiu_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Obra vial",
        context_excerpt=_SAMPLE_PRESUPUESTO_TAIL,
    )
    assert result is not None
    assert result.percentage == 30.0
    assert result.extraction_method == "llm"
