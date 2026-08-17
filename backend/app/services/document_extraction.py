"""Orchestrates extraction and storage of SECOP tender documents (user story 1.2)."""
from datetime import datetime
from typing import Optional
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.secop_documents import (
    SecopDocumentDTO,
    build_document_object_key,
    build_document_storage_path,
    download_document_file,
    fetch_documents_for_portfolio,
)
from app.services.document_storage import get_document_storage
from app.services.secop_client import fetch_portfolio_id_for_external_id

logger = get_logger(__name__)


def _upsert_document_record(
    db: Session,
    tender: Tender,
    document: SecopDocumentDTO,
    object_key: str,
) -> TenderDocument:
    existing = (
        db.query(TenderDocument)
        .filter(
            TenderDocument.tender_id == tender.id,
            TenderDocument.external_document_id == document.external_document_id,
        )
        .first()
    )

    relative_path = object_key

    if existing:
        existing.document_type = document.document_type.value
        existing.file_name = document.file_name
        existing.file_path = relative_path
        existing.download_url = document.download_url
        existing.file_size = document.file_size
        existing.extension = document.extension
        existing.description = document.description
        existing.downloaded_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        return existing

    record = TenderDocument(
        tender_id=tender.id,
        external_document_id=document.external_document_id,
        document_type=document.document_type.value,
        file_name=document.file_name,
        file_path=relative_path,
        download_url=document.download_url,
        file_size=document.file_size,
        extension=document.extension,
        description=document.description,
        downloaded_at=datetime.utcnow(),
    )
    db.add(record)
    return record


def extract_documents_for_tender(db: Session, tender: Tender) -> int:
    """
    Download key documents for one tender and persist metadata.

    Returns the number of documents successfully stored.
    """
    if not settings.DOCUMENT_EXTRACTION_ENABLED:
        return 0

    if not tender.portfolio_id:
        portfolio_id = fetch_portfolio_id_for_external_id(tender.external_id)
        if portfolio_id:
            tender.portfolio_id = portfolio_id
            db.flush()
        else:
            logger.debug("Tender %s has no portfolio_id, skipping documents", tender.external_id)
            return 0

    documents = fetch_documents_for_portfolio(tender.portfolio_id)
    if not documents:
        logger.info("No key documents found for tender %s", tender.external_id)
        return 0

    storage = get_document_storage()
    saved_count = 0
    for document in documents:
        object_key = build_document_object_key(
            tender.external_id,
            document.document_type,
            document.file_name,
            document.external_document_id,
        )
        destination = build_document_storage_path(
            tender.external_id,
            document.document_type,
            document.file_name,
            document.external_document_id,
        )

        if not download_document_file(document, destination):
            continue

        try:
            storage.persist_local_file(destination, object_key)
        except Exception as exc:
            logger.error(
                "Failed to persist document %s for tender %s: %s",
                object_key,
                tender.external_id,
                exc,
                exc_info=True,
            )
            continue

        _upsert_document_record(db, tender, document, object_key)
        saved_count += 1

    if saved_count:
        logger.info(
            "Saved %s documents for tender %s (%s)",
            saved_count,
            tender.external_id,
            tender.reference,
        )

    return saved_count


def extract_documents_for_pending_tenders(
    db: Session,
    limit: Optional[int] = None,
) -> dict[str, int]:
    """
    Process tenders that have portfolio_id but no downloaded documents yet.

    Used after ingestion and for backfill batches.
    """
    batch_limit = limit or settings.DOCUMENT_EXTRACTION_BATCH_SIZE

    tenders = (
        db.query(Tender)
        .filter(~Tender.documents.any())
        .order_by(Tender.created_at.desc())
        .limit(batch_limit)
        .all()
    )

    processed = 0
    documents_saved = 0

    for tender in tenders:
        try:
            saved = extract_documents_for_tender(db, tender)
            documents_saved += saved
            processed += 1
            db.commit()
        except Exception as exc:
            logger.error(
                "Document extraction failed for tender %s: %s",
                tender.external_id,
                exc,
                exc_info=True,
            )
            db.rollback()

    logger.info(
        "Document extraction batch complete: %s tenders processed, %s files saved",
        processed,
        documents_saved,
    )
    return {"tenders_processed": processed, "documents_saved": documents_saved}
