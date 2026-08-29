"""Resolve a local filesystem path for a stored PDF document."""
from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.models.tender_document import TenderDocument
from app.services.document_storage import DocumentStorageService


@contextmanager
def local_pdf_path(
    document: TenderDocument,
    storage: DocumentStorageService,
) -> Iterator[Path]:
    """Yield a local path to the PDF, downloading to a temp file if needed."""
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        local_path = storage.local_path(document.file_path)
        if local_path.is_file():
            yield local_path
            return

        temp_dir = tempfile.TemporaryDirectory(prefix="licitia_pdf_")
        pdf_path = Path(temp_dir.name) / Path(document.file_name).name
        with pdf_path.open("wb") as handle:
            for chunk in storage.iter_file_chunks(document.file_path):
                handle.write(chunk)
        yield pdf_path
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
