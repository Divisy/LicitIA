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
    count_processed_tenders_for_resync,
    deduplicate_visible_documents,
    extract_compressed_documents_for_tender,
    extract_documents_for_pending_tenders,
    processed_document_resync_query,
    resync_documents_for_processed_tenders,
)
from app.services.document_storage import get_document_storage
from app.services.secop_document_filters import normalize_document_filename

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


def reconcile_duplicate_documents(db: Session, fix: bool = False) -> dict[str, int]:
    """
    Remove duplicate tender_documents rows that share type + normalized filename.

    SECOP may publish multiple catalog ids for the same file. Keeps the newest row
    and deletes duplicate metadata plus unused blobs from storage.
    """
    storage = get_document_storage()
    groups: dict[tuple, list[TenderDocument]] = {}
    for document in db.query(TenderDocument).order_by(TenderDocument.created_at.asc()).all():
        key = (
            document.tender_id,
            document.document_type,
            normalize_document_filename(document.file_name),
        )
        groups.setdefault(key, []).append(document)

    duplicates: list[TenderDocument] = []
    duplicate_groups = 0
    keeper_paths: set[str] = set()

    for group in groups.values():
        if len(group) == 1:
            keeper_paths.add(group[0].file_path)
            continue
        duplicate_groups += 1
        keeper = deduplicate_visible_documents(group)[0]
        keeper_paths.add(keeper.file_path)
        duplicates.extend(document for document in group if document.id != keeper.id)

    stats = {
        "duplicate_groups": duplicate_groups,
        "duplicate_rows": len(duplicates),
        "blobs_deleted": 0,
        "rows_deleted": 0,
    }
    if not fix or not duplicates:
        return stats

    for duplicate in duplicates:
        if duplicate.file_path not in keeper_paths:
            try:
                storage.delete_object(duplicate.file_path)
                stats["blobs_deleted"] += 1
            except Exception as exc:
                logger.warning(
                    "Failed to delete duplicate blob %s: %s",
                    duplicate.file_path,
                    exc,
                )
        db.delete(duplicate)
        stats["rows_deleted"] += 1

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


def reset_document_extraction_attempts(
    db: Session,
    *,
    dry_run: bool = False,
    external_id: Optional[str] = None,
    reference: Optional[str] = None,
) -> dict[str, int]:
    """
    Clear documents_extraction_attempted_at for tenders without archived documents.

    Used after classifier improvements (US 1.2.3) so backfill can retry them.
    """
    query = (
        db.query(Tender)
        .filter(~Tender.documents.any())
        .filter(Tender.documents_extraction_attempted_at.isnot(None))
    )

    if external_id:
        query = query.filter(Tender.external_id == external_id)
    if reference:
        query = query.filter(Tender.reference == reference)

    tenders = query.all()
    stats = {
        "eligible_for_reset": len(tenders),
        "reset_count": 0,
    }

    if dry_run or not tenders:
        return stats

    for tender in tenders:
        tender.documents_extraction_attempted_at = None

    db.commit()
    stats["reset_count"] = len(tenders)
    return stats


def run_document_resync(
    db: Session,
    *,
    max_batches: Optional[int] = None,
    batch_size: Optional[int] = None,
    pause_seconds: float = 2.0,
    dry_run: bool = False,
    only_without_pliego: bool = False,
    external_id: Optional[str] = None,
    reference: Optional[str] = None,
) -> dict[str, int]:
    """
    Incrementally re-sync SECOP key documents for already-processed tenders.

    Used after classifier improvements (US 1.2.3+) to pick up documents that
    were skipped on the first extraction pass.
    """
    eligible_query = processed_document_resync_query(
        db,
        only_without_pliego=only_without_pliego,
    )
    if external_id:
        eligible_query = eligible_query.filter(Tender.external_id == external_id)
    if reference:
        eligible_query = eligible_query.filter(Tender.reference == reference)

    eligible = eligible_query.count()

    if dry_run:
        summary = summarize_document_storage(db)
        return {
            **summary,
            "eligible_for_resync": eligible,
            "batches_run": 0,
        }

    tender_ids = [row[0] for row in eligible_query.with_entities(Tender.id).all()]

    totals = {
        "eligible_for_resync": eligible,
        "batches_run": 0,
        "tenders_processed": 0,
        "tenders_with_new_docs": 0,
        "documents_saved": 0,
        "documents_added": 0,
        "documents_updated": 0,
        "no_portfolio": 0,
        "no_secop_docs": 0,
        "download_failures": 0,
        "errors": 0,
    }

    effective_batch_size = batch_size or settings.DOCUMENT_EXTRACTION_BATCH_SIZE
    batches_left = max_batches

    for offset in range(0, len(tender_ids), effective_batch_size):
        if batches_left is not None and batches_left <= 0:
            break

        chunk_ids = tender_ids[offset : offset + effective_batch_size]
        tenders = db.query(Tender).filter(Tender.id.in_(chunk_ids)).all()
        if not tenders:
            break

        batch_stats = resync_documents_for_processed_tenders(db, tenders)
        totals["batches_run"] += 1
        for key in (
            "tenders_processed",
            "tenders_with_new_docs",
            "documents_saved",
            "documents_added",
            "documents_updated",
            "no_portfolio",
            "no_secop_docs",
            "download_failures",
            "errors",
        ):
            totals[key] += batch_stats.get(key, 0)

        if batch_stats.get("tenders_processed", 0) == 0:
            break

        if batches_left is not None:
            batches_left -= 1

        if offset + effective_batch_size < len(tender_ids) and pause_seconds > 0:
            time.sleep(pause_seconds)

    totals["eligible_for_resync_remaining"] = eligible_query.count()
    totals["tenders_with_documents"] = (
        db.query(TenderDocument.tender_id).distinct().count()
    )
    return totals


def run_compressed_document_extraction(
    db: Session,
    *,
    max_batches: Optional[int] = None,
    batch_size: Optional[int] = None,
    pause_seconds: float = 2.0,
    dry_run: bool = False,
    external_id: Optional[str] = None,
    reference: Optional[str] = None,
) -> dict[str, int]:
    """Reprocess SECOP archives for already-ingested tenders (US 1.2.4)."""
    query = processed_document_resync_query(db)
    if external_id:
        query = query.filter(Tender.external_id == external_id)
    if reference:
        query = query.filter(Tender.reference == reference)

    eligible = query.count()
    if dry_run:
        summary = summarize_document_storage(db)
        return {**summary, "eligible_for_archive_extraction": eligible, "batches_run": 0}

    tender_ids = [row[0] for row in query.with_entities(Tender.id).all()]
    totals = {
        "eligible_for_archive_extraction": eligible,
        "batches_run": 0,
        "tenders_processed": 0,
        "archives_processed": 0,
        "archives_failed": 0,
        "documents_saved": 0,
        "documents_added": 0,
        "containers_removed": 0,
        "errors": 0,
    }

    effective_batch_size = batch_size or settings.DOCUMENT_EXTRACTION_BATCH_SIZE
    batches_left = max_batches

    for offset in range(0, len(tender_ids), effective_batch_size):
        if batches_left is not None and batches_left <= 0:
            break

        chunk_ids = tender_ids[offset : offset + effective_batch_size]
        tenders = db.query(Tender).filter(Tender.id.in_(chunk_ids)).all()
        if not tenders:
            break

        totals["batches_run"] += 1
        for tender in tenders:
            try:
                result = extract_compressed_documents_for_tender(db, tender)
                totals["tenders_processed"] += 1
                totals["archives_processed"] += result.archives_processed
                totals["archives_failed"] += result.archives_failed
                totals["documents_saved"] += result.documents_saved
                totals["documents_added"] += result.documents_added
                totals["containers_removed"] += result.containers_removed
                if result.errors:
                    totals["errors"] += len(result.errors)
                db.commit()
            except Exception as exc:
                logger.error(
                    "Compressed document extraction failed for tender %s: %s",
                    tender.external_id,
                    exc,
                    exc_info=True,
                )
                db.rollback()
                totals["errors"] += 1

        if batches_left is not None:
            batches_left -= 1

        if offset + effective_batch_size < len(tender_ids) and pause_seconds > 0:
            time.sleep(pause_seconds)

    totals["tenders_with_documents"] = (
        db.query(TenderDocument.tender_id).distinct().count()
    )
    return totals
