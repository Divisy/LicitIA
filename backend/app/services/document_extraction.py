"""Orchestrates extraction and storage of SECOP tender documents (user story 1.2)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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


@dataclass
class TenderExtractionResult:
    """Outcome of document extraction for a single tender."""

    documents_saved: int = 0
    outcome: str = "saved"
    download_failures: int = 0


@dataclass
class ExtractionBatchStats:
    """Aggregated stats for a batch of tender extractions."""

    tenders_processed: int = 0
    documents_saved: int = 0
    no_portfolio: int = 0
    no_secop_docs: int = 0
    download_failures: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "tenders_processed": self.tenders_processed,
            "documents_saved": self.documents_saved,
            "no_portfolio": self.no_portfolio,
            "no_secop_docs": self.no_secop_docs,
            "download_failures": self.download_failures,
            "errors": self.errors,
        }


def pending_document_extraction_query(db: Session):
    """Tenders not yet attempted for document extraction and without stored documents."""
    return (
        db.query(Tender)
        .filter(
            Tender.documents_extraction_attempted_at.is_(None),
            ~Tender.documents.any(),
        )
        .order_by(Tender.created_at.desc())
    )


def count_pending_document_extractions(db: Session) -> int:
    return pending_document_extraction_query(db).count()


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


def _mark_extraction_attempted(tender: Tender) -> None:
    tender.documents_extraction_attempted_at = datetime.utcnow()
    tender.updated_at = datetime.utcnow()


def extract_documents_for_tender(db: Session, tender: Tender) -> TenderExtractionResult:
    """
    Download key documents for one tender and persist metadata.

    Marks the tender as attempted even when SECOP has no key documents.
    """
    if not settings.DOCUMENT_EXTRACTION_ENABLED:
        return TenderExtractionResult(outcome="disabled")

    if not tender.portfolio_id:
        portfolio_id = fetch_portfolio_id_for_external_id(tender.external_id)
        if portfolio_id:
            tender.portfolio_id = portfolio_id
            db.flush()
        else:
            logger.debug("Tender %s has no portfolio_id, skipping documents", tender.external_id)
            _mark_extraction_attempted(tender)
            return TenderExtractionResult(outcome="no_portfolio")

    documents = fetch_documents_for_portfolio(tender.portfolio_id)
    if not documents:
        logger.info("No key documents found for tender %s", tender.external_id)
        _mark_extraction_attempted(tender)
        return TenderExtractionResult(outcome="no_secop_docs")

    storage = get_document_storage()
    saved_count = 0
    download_failures = 0
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
            download_failures += 1
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
            download_failures += 1
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
        outcome = "saved" if download_failures == 0 else "partial"
        _mark_extraction_attempted(tender)
    elif download_failures:
        outcome = "download_failed"
    else:
        outcome = "no_secop_docs"
        _mark_extraction_attempted(tender)

    return TenderExtractionResult(
        documents_saved=saved_count,
        outcome=outcome,
        download_failures=download_failures,
    )


def extract_documents_for_pending_tenders(
    db: Session,
    limit: Optional[int] = None,
) -> dict[str, int]:
    """
    Process tenders that have not yet been attempted for document extraction.

    Used after ingestion, for scheduled jobs, and for historical backfill batches.
    """
    batch_limit = limit or settings.DOCUMENT_EXTRACTION_BATCH_SIZE
    tenders = pending_document_extraction_query(db).limit(batch_limit).all()

    stats = ExtractionBatchStats()

    for tender in tenders:
        try:
            result = extract_documents_for_tender(db, tender)
            if result.outcome == "disabled":
                break
            stats.tenders_processed += 1
            stats.documents_saved += result.documents_saved
            stats.download_failures += result.download_failures
            if result.outcome == "no_portfolio":
                stats.no_portfolio += 1
            elif result.outcome == "no_secop_docs":
                stats.no_secop_docs += 1
            elif result.outcome == "download_failed":
                stats.errors += 1
            db.commit()
        except Exception as exc:
            logger.error(
                "Document extraction failed for tender %s: %s",
                tender.external_id,
                exc,
                exc_info=True,
            )
            db.rollback()
            stats.errors += 1

    logger.info(
        "Document extraction batch complete: %s tenders processed, %s files saved",
        stats.tenders_processed,
        stats.documents_saved,
    )
    return stats.as_dict()
