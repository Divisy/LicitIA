"""Tests for scanned presupuesto vision (US 1.4)."""
import json
from unittest.mock import MagicMock, patch

from app.services.tender_summary.llm_extraction import extract_aiu_with_vision, resolve_aiu_extraction
from app.services.tender_summary.pdf_ocr import (
    is_pdf_text_insufficient,
    select_presupuesto_vision_pages,
)
from app.services.tender_summary.presupuesto_extraction import (
    extract_aiu_percentage_from_text,
    has_presupuesto_aiu_context,
    is_credible_aiu_extraction,
)

_OCR_PAGE_1_TEXT = """
PRESUPUESTO DE OBRA
SUBTOTAL $994.059.917
(A.I.U. = 30%)
ADMINISTRACION (A=24%) $238.574.380
IMPREVISTOS (I=1%) $9.940.599
UTILIDAD (U=5%) $49.702.996
"""

_PLIEGO_EXPERIENCIA_TEXT = """
3.1 EXPERIENCIA GENERAL equivalente al treinta por ciento (30%) del presupuesto oficial.
4. EXPERIENCIA ESPECIFICA equivalente al veinte por ciento (20%) del presupuesto oficial.
"""


def test_is_pdf_text_insufficient_detects_scanned_pdf():
    assert is_pdf_text_insufficient("", [], min_chars=80) is True
    assert is_pdf_text_insufficient("texto corto", [], min_chars=80) is True
    assert is_pdf_text_insufficient("x" * 120, [], min_chars=80) is False


def test_select_presupuesto_vision_pages_only_first_page():
    assert select_presupuesto_vision_pages(1) == [1]
    assert select_presupuesto_vision_pages(19) == [1]


def test_presupuesto_aiu_text_is_recognized():
    parsed = extract_aiu_percentage_from_text(_OCR_PAGE_1_TEXT)
    assert parsed.aiu_percentage == 30.0
    assert has_presupuesto_aiu_context(_OCR_PAGE_1_TEXT) is True


def test_pliego_experiencia_text_is_not_aiu_context():
    assert has_presupuesto_aiu_context(_PLIEGO_EXPERIENCIA_TEXT) is False
    parsed = extract_aiu_percentage_from_text(_PLIEGO_EXPERIENCIA_TEXT)
    assert parsed.aiu_percentage is None


def test_is_credible_aiu_rejects_experiencia_evidence():
    from app.services.tender_summary.presupuesto_extraction import PresupuestoExtraction

    parsed = PresupuestoExtraction(aiu_percentage=20.0)
    assert is_credible_aiu_extraction(
        parsed,
        evidence="experiencia especifica equivalente al 20% del presupuesto oficial",
    ) is False


def test_is_credible_aiu_rejects_garbage_decimal_components():
    from app.services.tender_summary.presupuesto_extraction import PresupuestoExtraction

    parsed = PresupuestoExtraction(
        aiu_percentage=0.53,
        aiu_admin_percentage=0.24,
        aiu_imprevistos_percentage=0.05,
        aiu_utilidad_percentage=0.24,
    )
    assert is_credible_aiu_extraction(parsed, evidence="A.I.U.= 0.53%") is False


def test_normalize_aiu_fixes_decimal_misread():
    from app.services.tender_summary.presupuesto_extraction import (
        PresupuestoExtraction,
        normalize_aiu_percentages,
    )

    parsed = PresupuestoExtraction(
        aiu_percentage=0.3,
        aiu_admin_percentage=0.24,
        aiu_imprevistos_percentage=0.01,
        aiu_utilidad_percentage=0.05,
    )
    fixed = normalize_aiu_percentages(parsed)
    assert fixed.aiu_percentage == 30.0
    assert fixed.aiu_admin_percentage == 24.0


def test_is_credible_aiu_accepts_components_sum():
    from app.services.tender_summary.presupuesto_extraction import PresupuestoExtraction

    parsed = PresupuestoExtraction(
        aiu_percentage=30.0,
        aiu_admin_percentage=24.0,
        aiu_imprevistos_percentage=1.0,
        aiu_utilidad_percentage=5.0,
    )
    assert is_credible_aiu_extraction(parsed, evidence="A.I.U.=30%") is True


@patch("app.services.tender_summary.llm_extraction._openai_client")
@patch("app.services.tender_summary.llm_extraction.settings")
def test_extract_aiu_with_vision_returns_formatted_display(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_USE_LLM_FOR_AIU = True
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL = "gpt-4o-mini"
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_DETAIL = "high"
    mock_settings.TENDER_SUMMARY_AIU_LLM_MIN_CONFIDENCE = 0.70
    message = MagicMock()
    message.content = json.dumps(
        {
            "aiu_percentage": 30,
            "admin_percentage": 24,
            "imprevistos_percentage": 1,
            "utilidad_percentage": 5,
            "display_value": "AIU del 20% del presupuesto",
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
        page_images=[(1, b"fake-png")],
    )
    assert result is not None
    assert result.percentage == 30.0
    assert "30.00%" in result.display_value
    assert "A 24%" in result.display_value
    assert "20%" not in result.display_value


def test_resolve_aiu_ignores_pliego_experiencia_without_aiu_markers():
    with patch(
        "app.services.tender_summary.llm_extraction.extract_aiu_with_vision"
    ) as mock_vision:
        mock_vision.return_value = None
        result = resolve_aiu_extraction(
            tender_external_id="CO1.REQ.1",
            object_text="Obra",
            excerpt=_PLIEGO_EXPERIENCIA_TEXT,
            fallback_text=_PLIEGO_EXPERIENCIA_TEXT,
            vision_page_images=None,
        )
    assert result is None
    mock_vision.assert_not_called()


def test_resolve_aiu_uses_vision_for_scanned_presupuesto():
    with patch(
        "app.services.tender_summary.llm_extraction.extract_aiu_with_vision"
    ) as mock_vision:
        mock_vision.return_value = MagicMock(
            percentage=30.0,
            display_value="30.00% (A 24% · I 1% · U 5%)",
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
    assert result.percentage == 30.0
    mock_vision.assert_called_once()
