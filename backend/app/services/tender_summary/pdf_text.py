"""Extract text from stored PDF documents."""
from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService

logger = get_logger(__name__)
_MAX_PAGES = 80


def extract_pdf_text(document: TenderDocument, storage: DocumentStorageService) -> str:
    """Read up to the first N pages of a PDF from storage."""
    if (document.extension or "").lower() != "pdf":
        return ""

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        local_path = storage.local_path(document.file_path)
        if local_path.is_file():
            pdf_path = local_path
        else:
            temp_dir = tempfile.TemporaryDirectory(prefix="licitia_pdf_")
            pdf_path = Path(temp_dir.name) / Path(document.file_name).name
            with pdf_path.open("wb") as handle:
                for chunk in storage.iter_file_chunks(document.file_path):
                    handle.write(chunk)

        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        chunks: list[str] = []
        for page in reader.pages[:_MAX_PAGES]:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
        return "\n".join(chunks)
    except Exception as exc:
        logger.warning("Failed to extract PDF text from %s: %s", document.file_name, exc)
        return ""
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
