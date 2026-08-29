"""Tests for scanned presupuesto vision (US 1.4)."""
import json
from unittest.mock import MagicMock, patch

from app.services.tender_summary.llm_extraction import extract_aiu_with_vision, resolve_aiu_extraction
from app.services.tender_summary.pdf_ocr import (
    is_pdf_text_insufficient,
    select_presupuesto_vision_pages,
    vision_detail_level,
)
from app.services.tender_summary.presupuesto_extraction import extract_aiu_percentage_from_text

_OCR_PAGE_1_TEXT = """
PRESUPUESTO DE OBRA
SUBTOTAL $994.059.917
(A.I.U. = 30%)
ADMINISTRACION (A=24%) $238.574.380
IMPREVISTOS (I=1%) $9.940.599
UTILIDAD (U=5%) $49.702.996
"""


def test_is_pdf_text_insufficient_detects_scanned_pdf():
    assert is_pdf_text_insufficient("", [], min_chars=80) is True
    assert is_pdf_text_insufficient("texto corto", [], min_chars=80) is True
    assert is_pdf_text_insufficient("x" * 120, [], min_chars=80) is False


def test_select_presupuesto_vision_pages_only_first_page():
    assert select_presupuesto_vision_pages(1) == [1]
    assert select_presupuesto_vision_pages(19) == [1]


def test_ocr_text_feeds_aiu_regex():
    parsed = extract_aiu_percentage_from_text(_OCR_PAGE_1_TEXT)
    assert parsed.aiu_percentage == 30.0
    assert parsed.aiu_admin_percentage == 24.0


@patch("app.services.tender_summary.llm_extraction.settings")
def test_vision_detail_defaults_to_low(mock_settings):
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_DETAIL = "low"
    assert vision_detail_level() == "low"


@patch("app.services.tender_summary.llm_extraction._openai_client")
@patch("app.services.tender_summary.llm_extraction.settings")
def test_extract_aiu_with_vision_uses_single_page_and_low_detail(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_USE_LLM_FOR_AIU = True
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL = "gpt-4o-mini"
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_DETAIL = "low"
    mock_settings.TENDER_SUMMARY_AIU_LLM_MIN_CONFIDENCE = 0.70
    message = MagicMock()
    message.content = json.dumps(
        {
            "aiu_percentage": 30,
            "admin_percentage": 24,
            "imprevistos_percentage": 1,
            "utilidad_percentage": 5,
            "display_value": "30% (A 24% · I 1% · U 5%)",
            "confidence": 0.95,
            "evidence": "A.I.U. = 30%",
        }
    )
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create.return_value = response

    result = extract_aiu_with_vision(
        tender_external_id="CO1.REQ.1",
        object_text="Alumbrado público",
        page_images=[(1, b"fake-png"), (2, b"ignored")],
    )
    assert result is not None
    assert result.percentage == 30.0
    assert result.extraction_method == "vision"

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][1]["content"]
    image_parts = [part for part in user_content if part.get("type") == "image_url"]
    assert len(image_parts) == 1
    assert image_parts[0]["image_url"]["detail"] == "low"


def test_resolve_aiu_prefers_vision_for_scanned_presupuesto():
    with patch(
        "app.services.tender_summary.llm_extraction.extract_aiu_with_vision"
    ) as mock_vision:
        mock_vision.return_value = MagicMock(
            percentage=30.0,
            display_value="30%",
            confidence=0.9,
            extraction_method="vision",
        )
        result = resolve_aiu_extraction(
            tender_external_id="CO1.REQ.1",
            object_text="Obra",
            excerpt="",
            fallback_text="",
            vision_page_images=[(1, b"png")],
        )
    assert result is not None
    assert result.extraction_method == "vision"
    mock_vision.assert_called_once()
