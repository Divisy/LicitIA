"""Tests for missing key document sync and DOCX text extraction."""
import io
import zipfile
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.document_extraction import ensure_missing_key_documents_for_tender
from app.services.document_text import extract_docx_text
from app.services.secop_document_filters import DocumentType
from app.services.secop_documents import SecopDocumentDTO


def _build_minimal_docx(text: str) -> bytes:
    buffer = io.BytesIO()
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def test_extract_docx_text_reads_paragraphs(tmp_path):
    docx_path = tmp_path / "matriz.docx"
    docx_path.write_bytes(_build_minimal_docx("Indice de liquidez mayor o igual a 1.2"))

    document = TenderDocument(
        id=uuid4(),
        tender_id=uuid4(),
        external_document_id="test-docx",
        document_type="indicadores_financieros",
        file_name="matriz.docx",
        file_path="test/matriz.docx",
        extension="docx",
    )
    storage = MagicMock()
    storage.local_path.return_value = docx_path

    text = extract_docx_text(document, storage)
    assert "Indice de liquidez" in text
    assert "1.2" in text


@patch("app.services.document_extraction._upsert_document_record")
@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.fetch_loose_key_documents_for_portfolio")
@patch("app.services.document_extraction.download_document_file", return_value=True)
@patch("app.services.document_extraction.get_document_storage")
def test_ensure_missing_key_documents_downloads_new_type(
    mock_storage_factory,
    _mock_download,
    mock_fetch,
    mock_settings,
    mock_upsert,
):
    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True
    mock_upsert.return_value = (MagicMock(), True)

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST",
        portfolio_id="CO1.BDOS.1",
        reference="CMA-DEO-SGI-049-2026",
        source="secop_ii",
        entity_name="Entity",
        object_text="Test",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = [
        TenderDocument(
            id=uuid4(),
            tender_id=tender.id,
            external_document_id="pliego-1",
            document_type="pliego_condiciones",
            file_name="pliego.pdf",
            file_path="path/pliego.pdf",
            extension="pdf",
        )
    ]

    mock_fetch.return_value = [
        SecopDocumentDTO(
            external_document_id="836628505",
            portfolio_id="CO1.BDOS.1",
            file_name="Matriz 2 - Indicadores Financieros y Organizacionales.docx",
            download_url="https://example.com/doc.docx",
            extension="docx",
            document_type=DocumentType.INDICADORES_FINANCIEROS,
        )
    ]

    storage = MagicMock()
    mock_storage_factory.return_value = storage

    db = MagicMock()
    synced = ensure_missing_key_documents_for_tender(db, tender)

    assert synced == 1
    storage.persist_local_file.assert_called_once()


@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.fetch_loose_key_documents_for_portfolio")
@patch("app.services.document_extraction.download_document_file", return_value=True)
@patch("app.services.document_extraction.get_document_storage")
def test_ensure_missing_key_documents_reclassifies_existing_otro(
    mock_storage_factory,
    _mock_download,
    mock_fetch,
    mock_settings,
):
    """Documents saved as otro before indicadores_financieros existed must be reclassified."""
    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST",
        portfolio_id="CO1.BDOS.1",
        reference="CMA-DEO-SGI-049-2026",
        source="secop_ii",
        entity_name="Entity",
        object_text="Test",
        state="Publicado",
        process_url="https://example.com",
    )
    existing = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        external_document_id="836628505",
        document_type="otro",
        file_name="Matriz 2 - Indicadores Financieros y Organizacionales.docx",
        file_path="path/otro/matriz.docx",
        extension="docx",
        download_url="https://example.com/old",
    )
    tender.documents = [existing]

    mock_fetch.return_value = [
        SecopDocumentDTO(
            external_document_id="836628505",
            portfolio_id="CO1.BDOS.1",
            file_name="Matriz 2 - Indicadores Financieros y Organizacionales.docx",
            download_url="https://example.com/doc.docx",
            extension="docx",
            document_type=DocumentType.INDICADORES_FINANCIEROS,
        )
    ]

    storage = MagicMock()
    mock_storage_factory.return_value = storage

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    synced = ensure_missing_key_documents_for_tender(db, tender)

    assert synced == 1
    assert existing.document_type == "indicadores_financieros"
