"""Tests for document backfill and extraction queue logic (US 1.2.2 / 1.2.3)."""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.document_extraction import extract_documents_for_tender
from app.services.document_backfill import (
    reconcile_duplicate_documents,
    reconcile_orphan_documents,
    reset_document_extraction_attempts,
    run_document_resync,
)
from app.services.document_extraction import resync_documents_for_processed_tenders


@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.fetch_archive_candidates_for_portfolio", return_value=[])
@patch("app.services.document_extraction.fetch_loose_key_documents_for_portfolio", return_value=[])
@patch("app.services.document_extraction.fetch_portfolio_id_for_external_id", return_value="portfolio-1")
def test_extract_marks_attempted_when_secop_has_no_docs(mock_portfolio, mock_fetch, mock_archives, mock_settings):
    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True
    mock_settings.ARCHIVE_EXTRACTION_ENABLED = True

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.1",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Object",
        state="Publicado",
        process_url="https://example.com",
    )

    db = MagicMock()
    result = extract_documents_for_tender(db, tender)

    assert result.outcome == "no_secop_docs"
    assert result.documents_saved == 0
    assert tender.documents_extraction_attempted_at is not None


@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.fetch_portfolio_id_for_external_id", return_value=None)
def test_extract_marks_attempted_when_no_portfolio(mock_portfolio, mock_settings):
    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True

    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.2",
        portfolio_id=None,
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Object",
        state="Publicado",
        process_url="https://example.com",
    )

    db = MagicMock()
    result = extract_documents_for_tender(db, tender)

    assert result.outcome == "no_portfolio"
    assert tender.documents_extraction_attempted_at is not None


def test_reset_document_extraction_attempts_dry_run():
    tender = MagicMock()
    tender.documents_extraction_attempted_at = datetime.utcnow()

    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = [tender]

    stats = reset_document_extraction_attempts(db, dry_run=True)

    assert stats["eligible_for_reset"] == 1
    assert stats["reset_count"] == 0
    db.commit.assert_not_called()


@patch("app.services.document_backfill.get_document_storage")
def test_reconcile_orphans_dry_run(mock_storage_factory):
    storage = MagicMock()
    storage.exists.return_value = False
    mock_storage_factory.return_value = storage

    document = MagicMock()
    document.file_path = "CO1.REQ.1/pliego/x.pdf"
    document.tender_id = uuid4()

    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = [document]

    stats = reconcile_orphan_documents(db, fix=False)

    assert stats["orphans_found"] == 1
    assert stats["orphans_deleted"] == 0
    db.delete.assert_not_called()


@patch("app.services.document_backfill.resync_documents_for_processed_tenders")
@patch("app.services.document_backfill.processed_document_resync_query")
def test_run_document_resync_dry_run(mock_query, mock_resync):
    db = MagicMock()
    mock_query.return_value.count.return_value = 215

    with patch("app.services.document_backfill.summarize_document_storage", return_value={"total_tenders": 215}):
        stats = run_document_resync(db, dry_run=True)

    assert stats["eligible_for_resync"] == 215
    assert stats["batches_run"] == 0
    mock_resync.assert_not_called()


@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.extract_archives_for_tender")
@patch("app.services.document_extraction.get_document_storage")
@patch("app.services.document_extraction.download_document_file", return_value=True)
@patch("app.services.document_extraction.fetch_archive_candidates_for_portfolio", return_value=[])
@patch("app.services.document_extraction.fetch_loose_key_documents_for_portfolio")
def test_resync_adds_missing_documents(
    mock_fetch,
    mock_archives,
    mock_download,
    mock_storage_factory,
    mock_extract_archives,
    mock_settings,
):
    from app.services.archive_extraction import ArchiveExtractionResult
    from app.services.secop_document_filters import DocumentType
    from app.services.secop_documents import SecopDocumentDTO

    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True
    mock_settings.ARCHIVE_EXTRACTION_ENABLED = True
    mock_extract_archives.return_value = ArchiveExtractionResult()
    mock_storage_factory.return_value = MagicMock()

    existing_doc = MagicMock()
    existing_doc.external_document_id = "111"
    existing_doc.document_type = "presupuesto"

    tender = MagicMock()
    tender.id = uuid4()
    tender.external_id = "CO1.REQ.1"
    tender.portfolio_id = "portfolio-1"
    tender.reference = "LP-001"
    tender.documents = [existing_doc]

    mock_fetch.return_value = [
        SecopDocumentDTO(
            external_document_id="111",
            portfolio_id="portfolio-1",
            file_name="PRESUPUESTO.pdf",
            download_url="https://example.com/111",
            document_type=DocumentType.PRESUPUESTO,
        ),
        SecopDocumentDTO(
            external_document_id="222",
            portfolio_id="portfolio-1",
            file_name="PROYECTO DE PLIEGO.pdf",
            download_url="https://example.com/222",
            document_type=DocumentType.PLIEGO_CONDICIONES,
        ),
    ]

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [existing_doc, None]

    stats = resync_documents_for_processed_tenders(db, [tender])

    assert stats["tenders_processed"] == 1
    assert stats["documents_added"] == 1
    assert stats["documents_updated"] == 1
    assert stats["tenders_with_new_docs"] == 1
    db.commit.assert_called_once()


@patch("app.services.document_backfill.get_document_storage")
def test_reconcile_duplicate_documents_fix(mock_storage_factory):
    storage = MagicMock()
    mock_storage_factory.return_value = storage

    tender_id = uuid4()
    older = MagicMock()
    older.id = uuid4()
    older.tender_id = tender_id
    older.document_type = "pliego_condiciones"
    older.file_name = "Documento Base.docx"
    older.file_path = "CO1.REQ.1/pliego/old.docx"
    older.downloaded_at = datetime(2026, 1, 1)
    older.created_at = datetime(2026, 1, 1)

    newer = MagicMock()
    newer.id = uuid4()
    newer.tender_id = tender_id
    newer.document_type = "pliego_condiciones"
    newer.file_name = "Documento Base.docx"
    newer.file_path = "CO1.REQ.1/pliego/new.docx"
    newer.downloaded_at = datetime(2026, 2, 1)
    newer.created_at = datetime(2026, 2, 1)

    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = [older, newer]

    stats = reconcile_duplicate_documents(db, fix=True)

    assert stats["duplicate_groups"] == 1
    assert stats["duplicate_rows"] == 1
    assert stats["rows_deleted"] == 1
    assert stats["blobs_deleted"] == 1
    db.delete.assert_called_once_with(older)
    db.commit.assert_called_once()
