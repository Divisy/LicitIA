"""Tests for SECOP archive extraction (US 1.2.4)."""
import zipfile
from pathlib import Path

import pytest

from app.services.archive_extraction import (
    build_internal_document_id,
    extract_archive_members,
    is_archive_container_candidate,
    is_archive_excluded_by_name,
)
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import SecopDocumentDTO, is_archive_filename


def _archive_dto(file_name: str, doc_type: DocumentType = DocumentType.OTRO) -> SecopDocumentDTO:
    return SecopDocumentDTO(
        external_document_id="123456",
        portfolio_id="portfolio-1",
        file_name=file_name,
        download_url="https://example.com/archive",
        document_type=doc_type,
    )


def test_is_archive_filename():
    assert is_archive_filename("OTROS DOCUMENTOS.rar") is True
    assert is_archive_filename("pliego.pdf") is False


def test_is_archive_container_candidate_for_otros_documentos():
    document = _archive_dto("OTROS DOCUMENTOS.rar")
    assert is_archive_container_candidate(document) is True


def test_is_archive_container_candidate_excludes_planos():
    document = _archive_dto("planos_obra.zip")
    assert is_archive_excluded_by_name(document.file_name) is True
    assert is_archive_container_candidate(document) is False


def test_is_archive_container_candidate_for_presupuesto_rar():
    document = _archive_dto("1.2. PRESUPUESTO.rar", DocumentType.PRESUPUESTO)
    assert is_archive_container_candidate(document) is True


def test_build_internal_document_id():
    assert build_internal_document_id("999", "folder/pliego.pdf") == "999:folder/pliego.pdf"


def test_build_internal_document_id_truncates_long_paths():
    long_path = "ANEXOS - FORMATOS PRESENTACIÓN OFERTA/" + ("x" * 200) + ".docx"
    synthetic = build_internal_document_id("820462077", long_path)
    assert len(synthetic) <= 100
    assert synthetic.startswith("820462077:")
    assert synthetic == build_internal_document_id("820462077", long_path)


def test_extract_zip_members_classifies_inner_files(tmp_path: Path):
    archive_path = tmp_path / "formatos.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("pliego condiciones.pdf", b"pdf-content")
        archive.writestr("ignore.cad", b"cad")

    members = extract_archive_members(archive_path)
    assert len(members) == 1
    assert members[0].file_name == "pliego condiciones.pdf"


def test_extract_zip_members_enforces_file_limit(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.services.archive_extraction.settings.ARCHIVE_MAX_FILES", 1)
    archive_path = tmp_path / "many.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("one.pdf", b"1")
        archive.writestr("two.pdf", b"2")

    with pytest.raises(ValueError, match="maximum file count"):
        extract_archive_members(archive_path)
