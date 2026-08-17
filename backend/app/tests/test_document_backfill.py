"""Tests for document backfill and extraction queue logic (US 1.2.2)."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.document_extraction import extract_documents_for_tender
from app.services.document_backfill import reconcile_orphan_documents


@patch("app.services.document_extraction.settings")
@patch("app.services.document_extraction.fetch_documents_for_portfolio", return_value=[])
@patch("app.services.document_extraction.fetch_portfolio_id_for_external_id", return_value="portfolio-1")
def test_extract_marks_attempted_when_secop_has_no_docs(mock_portfolio, mock_fetch, mock_settings):
    mock_settings.DOCUMENT_EXTRACTION_ENABLED = True

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
