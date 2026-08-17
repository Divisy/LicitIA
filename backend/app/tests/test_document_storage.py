"""Tests for document object storage helpers."""
import tempfile
from pathlib import Path

import pytest

from app.config import settings
from app.services.document_storage import DocumentStorageService, normalize_object_key
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import build_document_object_key


def test_build_document_object_key():
    key = build_document_object_key(
        "CO1.REQ.10566487",
        DocumentType.PLIEGO_CONDICIONES,
        "Pliego Base.pdf",
        "816275942",
    )
    assert key == "CO1.REQ.10566487/pliego_condiciones/816275942_Pliego Base.pdf"


def test_normalize_object_key_rejects_traversal():
    with pytest.raises(ValueError):
        normalize_object_key("../secret.pdf")
    with pytest.raises(ValueError):
        normalize_object_key("/absolute/path.pdf")


def test_local_persist_keeps_file_on_disk(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(settings, "DOCUMENTS_STORAGE_PATH", tmpdir)
        monkeypatch.setattr(settings, "DOCUMENT_STORAGE_BACKEND", "local")
        monkeypatch.setattr(settings, "DOCUMENT_STORAGE_WRITE_LOCAL", True)

        storage = DocumentStorageService()
        source = Path(tmpdir) / "staging.pdf"
        source.write_bytes(b"pdf-content")
        key = "CO1.REQ.1/pliego_condiciones/1_test.pdf"

        returned_key = storage.persist_local_file(source, key)
        assert returned_key == key
        assert storage.local_path(key).read_bytes() == b"pdf-content"
        assert storage.exists(key)
