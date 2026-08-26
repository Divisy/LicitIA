"""Page-level PDF text extraction for requirement section navigation."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService

logger = get_logger(__name__)
_REQUIREMENTS_MAX_PAGES = 120


def extract_pdf_pages(
    document: TenderDocument,
    storage: DocumentStorageService,
    *,
    max_pages: int = _REQUIREMENTS_MAX_PAGES,
) -> list[tuple[int, str]]:
    """Return 1-based page numbers with extracted text."""
    if (document.extension or "").lower() != "pdf":
        return []

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        local_path = storage.local_path(document.file_path)
        if local_path.is_file():
            pdf_path = local_path
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="licitia_req_pdf_")
            pdf_path = Path(temp_dir.name) / Path(document.file_name).name
            with pdf_path.open("wb") as handle:
                for chunk in storage.iter_file_chunks(document.file_path):
                    handle.write(chunk)

        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        pages: list[tuple[int, str]] = []
        for index, page in enumerate(reader.pages[:max_pages]):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((index + 1, text))
        return pages
    except Exception as exc:
        logger.warning("Failed to extract PDF pages from %s: %s", document.file_name, exc)
        return []
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def join_pages(pages: list[tuple[int, str]]) -> str:
    return "\n".join(text for _, text in pages)
