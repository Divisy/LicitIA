"""Extract text from stored PDF documents."""
from __future__ import annotations

from app.core.logging import get_logger
from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService
from app.services.tender_summary.pdf_paths import local_pdf_path

logger = get_logger(__name__)
_MAX_PAGES = 80


def extract_pdf_text(document: TenderDocument, storage: DocumentStorageService) -> str:
    """Read up to the first N pages of a PDF from storage."""
    if (document.extension or "").lower() != "pdf":
        return ""

    try:
        with local_pdf_path(document, storage) as pdf_path:
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
