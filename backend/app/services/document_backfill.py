"""Historical document backfill and BD ↔ R2 reconciliation (US 1.2.2)."""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.services.document_extraction import (
    count_pending_document_extractions,
    extract_documents_for_pending_tenders,
)
from app.services.document_storage import get_document_storage

logger = get_logger(__name__)


def reconcile_orphan_documents(db: Session, fix: bool = False) -> dict[str, int]:
    """
    Find tender_documents rows whose blob is missing from storage (R2/local).

    When fix=True, delete orphan metadata and clear attempted_at on affected
    tenders so extraction can retry.
    """
    storage = get_document_storage()
    orphans: list[TenderDocument] = []

    for document in db.query(TenderDocument).order_by(TenderDocument.created_at.asc()).all():
        try:
            if not storage.exists(document.file_path):
                orphans.append(document)
        except ValueError:
            orphans.append(document)

    stats = {
        "orphans_found": len(orphans),
        "orphans_deleted": 0,
        "tenders_flagged_for_retry": 0,
    }

    if not fix or not orphans:
        return stats

    affected_tender_ids: set = set()
    for document in orphans:
        affected_tender_ids.add(document.tender_id)
        db.delete(document)

    db.flush()
    stats["orphans_deleted"] = len(orphans)

    for tender_id in affected_tender_ids:
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            continue
        if not tender.documents:
            tender.documents_extraction_attempted_at = None
            stats["tenders_flagged_for_retry"] += 1

    db.commit()
    return stats


def summarize_document_storage(db: Session) -> dict[str, int]:
    """High-level counts for backfill monitoring."""
    storage = get_document_storage()
    total_tenders = db.query(Tender).count()
    pending = count_pending_document_extractions(db)
    document_rows = db.query(TenderDocument).count()
    tenders_with_docs = (
        db.query(TenderDocument.tender_id).distinct().count()
    )

    missing_blobs = 0
    for document in db.query(TenderDocument).all():
        try:
            if not storage.exists(document.file_path):
                missing_blobs += 1
        except ValueError:
            missing_blobs += 1

    return {
        "total_tenders": total_tenders,
        "pending_extraction": pending,
        "tenders_with_documents": tenders_with_docs,
        "document_rows": document_rows,
        "orphan_metadata_rows": missing_blobs,
    }


def run_backfill(
    db: Session,
    *,
    max_batches: Optional[int] = None,
    batch_size: Optional[int] = None,
    pause_seconds: float = 2.0,
    reconcile_first: bool = True,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Run accelerated historical backfill in controlled batches.

    Returns aggregated stats across all batches executed.
    """
    if dry_run:
        summary = summarize_document_storage(db)
        reconcile_stats = reconcile_orphan_documents(db, fix=False)
        return {
            **summary,
            **{f"reconcile_{k}": v for k, v in reconcile_stats.items()},
            "batches_run": 0,
        }

    totals = {
        "batches_run": 0,
        "tenders_processed": 0,
        "documents_saved": 0,
        "no_portfolio": 0,
        "no_secop_docs": 0,
        "download_failures": 0,
        "errors": 0,
        "orphans_deleted": 0,
        "tenders_flagged_for_retry": 0,
    }

    if reconcile_first:
        reconcile_stats = reconcile_orphan_documents(db, fix=True)
        totals["orphans_deleted"] = reconcile_stats["orphans_deleted"]
        totals["tenders_flagged_for_retry"] = reconcile_stats["tenders_flagged_for_retry"]

    effective_batch_size = batch_size or settings.DOCUMENT_EXTRACTION_BATCH_SIZE
    batches_left = max_batches

    while count_pending_document_extractions(db) > 0:
        if batches_left is not None and batches_left <= 0:
            break

        batch_stats = extract_documents_for_pending_tenders(db, limit=effective_batch_size)
        totals["batches_run"] += 1
        for key in ("tenders_processed", "documents_saved", "no_portfolio", "no_secop_docs", "download_failures", "errors"):
            totals[key] += batch_stats.get(key, 0)

        if batch_stats.get("tenders_processed", 0) == 0:
            break

        if batches_left is not None:
            batches_left -= 1

        if count_pending_document_extractions(db) > 0 and pause_seconds > 0:
            time.sleep(pause_seconds)

    totals["pending_extraction_remaining"] = count_pending_document_extractions(db)
    totals["tenders_with_documents"] = (
        db.query(TenderDocument.tender_id).distinct().count()
    )
    return totals
