"""Vision helpers for scanned presupuesto PDFs (US 1.4)."""
from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService
from app.services.tender_summary.pdf_paths import local_pdf_path

logger = get_logger(__name__)


def is_pdf_text_insufficient(
    text: str,
    pages: list[tuple[int, str]],
    *,
    min_chars: int | None = None,
) -> bool:
    """Return True when the PDF likely has no text layer (scanned)."""
    threshold = min_chars or settings.TENDER_SUMMARY_PRESUPUESTO_OCR_MIN_TEXT_CHARS
    combined = (text or "").strip()
    if not combined and pages:
        combined = "\n".join(page_text for _, page_text in pages if page_text.strip())
    return len(combined) < threshold


def select_presupuesto_vision_pages(total_pages: int) -> list[int]:
    """Return page numbers to render for AIU vision (cheapest: summary page only)."""
    if total_pages <= 0:
        return []
    return [1]


def vision_detail_level() -> str:
    detail = (settings.TENDER_SUMMARY_PRESUPUESTO_VISION_DETAIL or "low").strip().lower()
    return detail if detail in {"low", "high", "auto"} else "low"


def _render_pdf_page_images(pdf_path: Path, page_numbers: list[int]) -> list[tuple[int, bytes]]:
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    try:
        images: list[tuple[int, bytes]] = []
        matrix = pymupdf.Matrix(
            settings.TENDER_SUMMARY_PRESUPUESTO_OCR_RENDER_SCALE,
            settings.TENDER_SUMMARY_PRESUPUESTO_OCR_RENDER_SCALE,
        )
        for page_no in page_numbers:
            if page_no < 1 or page_no > doc.page_count:
                continue
            pixmap = doc[page_no - 1].get_pixmap(matrix=matrix)
            images.append((page_no, pixmap.tobytes("png")))
        return images
    finally:
        doc.close()


def prepare_scanned_presupuesto_vision_images(
    document: TenderDocument,
    storage: DocumentStorageService,
    *,
    native_text: str,
    native_pages: list[tuple[int, str]],
) -> list[tuple[int, bytes]]:
    """
    Render page 1 for direct vision AIU extraction when the PDF has no text layer.

    Skips full-page OCR transcription to minimize API cost (one vision call only).
    """
    if not settings.TENDER_SUMMARY_PRESUPUESTO_OCR_ENABLED:
        return []
    if not is_pdf_text_insufficient(native_text, native_pages):
        return []
    if (document.extension or "").lower() != "pdf":
        return []

    try:
        with local_pdf_path(document, storage) as pdf_path:
            import pymupdf

            doc = pymupdf.open(str(pdf_path))
            try:
                page_numbers = select_presupuesto_vision_pages(doc.page_count)
            finally:
                doc.close()
            if not page_numbers:
                return []
            return _render_pdf_page_images(pdf_path, page_numbers)
    except Exception as exc:
        logger.warning("Failed to render presupuesto vision page for %s: %s", document.file_name, exc)
        return []
