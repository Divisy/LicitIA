"""Vision OCR for scanned presupuesto PDFs (US 1.4)."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService
from app.services.tender_summary.pdf_paths import local_pdf_path

logger = get_logger(__name__)

_openai_client: Optional[OpenAI] = None
if settings.OPENAI_API_KEY:
    _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

_PAGE_MARKER_RE = re.compile(r"^===PAGE (\d+)===\s*$", re.MULTILINE)


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


def select_presupuesto_ocr_pages(total_pages: int, *, max_pages: int | None = None) -> list[int]:
    """Pick pages likely to contain AIU: summary (page 1) + tail of Formulario 1."""
    if total_pages <= 0:
        return []
    limit = max_pages or settings.TENDER_SUMMARY_PRESUPUESTO_OCR_MAX_PAGES
    selected = [1]
    if total_pages > 1:
        tail_start = max(2, total_pages - 2)
        for page_no in range(tail_start, total_pages + 1):
            if page_no not in selected:
                selected.append(page_no)
            if len(selected) >= limit:
                break
    return sorted(selected)[:limit]


def _ocr_cache_path(document: TenderDocument) -> Path:
    base = Path(settings.DOCUMENTS_STORAGE_PATH) / "ocr_cache"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{document.id}.txt"


def _read_ocr_cache(document: TenderDocument) -> dict[int, str]:
    cache_path = _ocr_cache_path(document)
    if not cache_path.is_file():
        return {}

    try:
        raw = cache_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    header, _, body = raw.partition("\n")
    if not header.startswith("# ocr:v1:"):
        return {}
    if f"updated_at={document.updated_at.isoformat()}" not in header:
        return {}

    pages: dict[int, str] = {}
    current_page: int | None = None
    buffer: list[str] = []
    for line in body.splitlines():
        match = _PAGE_MARKER_RE.match(line)
        if match:
            if current_page is not None:
                pages[current_page] = "\n".join(buffer).strip()
            current_page = int(match.group(1))
            buffer = []
            continue
        buffer.append(line)
    if current_page is not None:
        pages[current_page] = "\n".join(buffer).strip()
    return pages


def _write_ocr_cache(document: TenderDocument, pages: dict[int, str]) -> None:
    cache_path = _ocr_cache_path(document)
    header = f"# ocr:v1:updated_at={document.updated_at.isoformat()}\n"
    chunks = [header]
    for page_no in sorted(pages):
        chunks.append(f"===PAGE {page_no}===\n{pages[page_no]}")
    try:
        cache_path.write_text("\n".join(chunks), encoding="utf-8")
    except OSError as exc:
        logger.warning("Failed to write OCR cache for %s: %s", document.file_name, exc)


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


def _vision_model_name() -> str:
    return settings.TENDER_SUMMARY_PRESUPUESTO_VISION_MODEL or settings.OPENAI_MODEL_NAME


def transcribe_page_images_with_vision(
    page_images: list[tuple[int, bytes]],
    *,
    purpose: str = "presupuesto",
) -> dict[int, str]:
    """OCR scanned PDF pages via OpenAI vision."""
    if not page_images or not _openai_client:
        return {}
    if not settings.TENDER_SUMMARY_PRESUPUESTO_OCR_ENABLED:
        return {}

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Transcribe todo el texto visible de estas páginas de un presupuesto oficial "
                "de obra pública colombiana (SECOP). Conserva números, porcentajes, símbolos "
                "y etiquetas como A.I.U., ADMINISTRACION, IMPREVISTOS, UTILIDAD, PRESUPUESTO DE OBRA. "
                f"Propósito: {purpose}. "
                "Responde JSON: {\"pages\": [{\"page\": number, \"text\": \"...\"}, ...]}."
            ),
        }
    ]
    for page_no, image_bytes in page_images:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content.append({"type": "text", "text": f"Página {page_no}:"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "high"},
            }
        )

    try:
        response = _openai_client.chat.completions.create(
            model=_vision_model_name(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un OCR experto en documentos de licitación colombiana. "
                        "Devuelve únicamente JSON válido."
                    ),
                },
                {"role": "user", "content": content},
            ],
            temperature=0.0,
            max_tokens=4_000,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception as exc:
        logger.warning("Vision OCR failed: %s", exc)
        return {}

    pages: dict[int, str] = {}
    for item in payload.get("pages") or []:
        if not isinstance(item, dict):
            continue
        page_no = item.get("page")
        text = (item.get("text") or "").strip()
        if isinstance(page_no, int) and text:
            pages[page_no] = text
    return pages


def extract_presupuesto_pdf_with_ocr(
    document: TenderDocument,
    storage: DocumentStorageService,
    *,
    native_text: str,
    native_pages: list[tuple[int, str]],
) -> tuple[str, list[tuple[int, str]], list[tuple[int, bytes]]]:
    """
    Return presupuesto text and pages, using vision OCR when the PDF has no text layer.

    Also returns rendered page images for a direct vision AIU fallback.
    """
    if not settings.TENDER_SUMMARY_PRESUPUESTO_OCR_ENABLED:
        return native_text, native_pages, []

    if not is_pdf_text_insufficient(native_text, native_pages):
        return native_text, native_pages, []

    if (document.extension or "").lower() != "pdf":
        return native_text, native_pages, []

    cached = _read_ocr_cache(document)
    if cached:
        pages = sorted(cached.items())
        return "\n\n".join(text for _, text in pages if text), pages, []

    try:
        with local_pdf_path(document, storage) as pdf_path:
            import pymupdf

            doc = pymupdf.open(str(pdf_path))
            try:
                page_numbers = select_presupuesto_ocr_pages(doc.page_count)
            finally:
                doc.close()
            if not page_numbers:
                return native_text, native_pages, []

            page_images = _render_pdf_page_images(pdf_path, page_numbers)
    except Exception as exc:
        logger.warning("Failed to prepare OCR for %s: %s", document.file_name, exc)
        return native_text, native_pages, []

    if not page_images:
        return native_text, native_pages, []

    ocr_pages = transcribe_page_images_with_vision(page_images)
    if not ocr_pages:
        return native_text, native_pages, page_images

    _write_ocr_cache(document, ocr_pages)
    ordered = sorted(ocr_pages.items())
    return "\n\n".join(text for _, text in ordered if text), ordered, page_images
