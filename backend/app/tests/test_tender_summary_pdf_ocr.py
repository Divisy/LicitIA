"""Tests for scanned presupuesto OCR (US 1.4)."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.tender_summary.llm_extraction import extract_aiu_with_vision, resolve_aiu_extraction
from app.services.tender_summary.pdf_ocr import (
    is_pdf_text_insufficient,
    select_presupuesto_ocr_pages,
    transcribe_page_images_with_vision,
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


def test_select_presupuesto_ocr_pages_prefers_first_and_tail():
    assert select_presupuesto_ocr_pages(1, max_pages=4) == [1]
    assert select_presupuesto_ocr_pages(19, max_pages=4) == [1, 17, 18, 19]


def test_ocr_text_feeds_aiu_regex():
    parsed = extract_aiu_percentage_from_text(_OCR_PAGE_1_TEXT)
    assert parsed.aiu_percentage == 30.0
    assert parsed.aiu_admin_percentage == 24.0


@patch("app.services.tender_summary.pdf_ocr._openai_client")
@patch("app.services.tender_summary.pdf_ocr.settings")
def test_transcribe_page_images_with_vision(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_OCR_ENABLED = True
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL = "gpt-4o-mini"
    message = MagicMock()
    message.content = json.dumps(
        {
            "pages": [
                {"page": 1, "text": _OCR_PAGE_1_TEXT},
            ]
        }
    )
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create.return_value = response

    pages = transcribe_page_images_with_vision([(1, b"fake-png")])
    assert 1 in pages
    assert "A.I.U." in pages[1]


@patch("app.services.tender_summary.llm_extraction._openai_client")
@patch("app.services.tender_summary.llm_extraction.settings")
def test_extract_aiu_with_vision(mock_settings, mock_client):
    mock_settings.TENDER_SUMMARY_USE_LLM_FOR_AIU = True
    mock_settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL = "gpt-4o-mini"
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
        page_images=[(1, b"fake-png")],
    )
    assert result is not None
    assert result.percentage == 30.0
    assert result.extraction_method == "vision"


def test_resolve_aiu_uses_vision_when_text_pipeline_fails():
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


@patch("app.services.tender_summary.pdf_ocr.settings")
def test_ocr_cache_roundtrip(mock_settings, tmp_path):
    from app.models.tender_document import TenderDocument
    from app.services.tender_summary import pdf_ocr

    mock_settings.DOCUMENTS_STORAGE_PATH = str(tmp_path)
    doc = TenderDocument(
        id=uuid4(),
        tender_id=uuid4(),
        external_document_id="doc-1",
        document_type="presupuesto",
        file_name="presupuesto.pdf",
        file_path="tenders/x/presupuesto.pdf",
        download_url="https://example.com/presupuesto.pdf",
        extension="pdf",
        updated_at=datetime(2025, 1, 15, 12, 0, 0),
    )
    pdf_ocr._write_ocr_cache(doc, {1: _OCR_PAGE_1_TEXT})
    cached = pdf_ocr._read_ocr_cache(doc)
    assert cached[1].startswith("PRESUPUESTO DE OBRA")
