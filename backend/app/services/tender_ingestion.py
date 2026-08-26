"""Tender ingestion service - fetches, stores, classifies, and notifies."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.tender import Tender, TenderSource
from app.models.subscription import Subscription
from app.services.secop_client import (
    SecopTenderDTO,
    fetch_mvp_secop_tenders,
    fetch_tenders_by_external_ids,
)
from app.config import settings
from app.services.tender_lifecycle import (
    purge_inactive_tenders,
    purge_tender,
)
from app.services.secop_filters import is_dashboard_active_tender
from app.services.notifications import send_email_alert, send_whatsapp_alert
from app.services.document_extraction import extract_documents_for_pending_tenders

logger = get_logger(__name__)


def _apply_secop_fields(target: Tender, secop_tender: SecopTenderDTO) -> None:
    """Copy SECOP fields from DTO onto a Tender model instance."""
    target.entity_name = secop_tender.entity_name
    target.reference = secop_tender.reference
    target.portfolio_id = secop_tender.portfolio_id
    target.object_text = secop_tender.object_text
    target.current_phase = secop_tender.current_phase
    target.department = secop_tender.department
    target.municipality = secop_tender.municipality
    target.amount = secop_tender.amount
    target.publication_date = secop_tender.publication_date
    target.closing_date = secop_tender.closing_date
    target.state = secop_tender.state
    target.apertura_estado = secop_tender.apertura_estado
    target.process_url = secop_tender.process_url
    target.contract_type = secop_tender.contract_type
    target.contract_modality = secop_tender.contract_modality
    target.unspsc_code = secop_tender.unspsc_code
    target.updated_at = datetime.utcnow()


def _tender_from_secop(secop_tender: SecopTenderDTO) -> Tender:
    """Build a new Tender from a SECOP DTO."""
    tender = Tender(
        external_id=secop_tender.external_id,
        source=TenderSource(secop_tender.source),
        is_relevant_interventoria_vial=False,
    )
    _apply_secop_fields(tender, secop_tender)
    return tender


def _persist_secop_batch(
    db: Session,
    secop_tenders: list[SecopTenderDTO],
) -> tuple[list[Tender], int]:
    """Insert new tenders and update existing ones from a SECOP batch."""
    new_tenders: list[Tender] = []
    updated_count = 0

    if not secop_tenders:
        return new_tenders, updated_count

    batch_size = 100
    for i in range(0, len(secop_tenders), batch_size):
        batch = secop_tenders[i : i + batch_size]
        batch_external_ids = [tender.external_id for tender in batch]
        existing_ids = set(
            row[0]
            for row in db.query(Tender.external_id)
            .filter(Tender.external_id.in_(batch_external_ids))
            .all()
        )

        for secop_tender in batch:
            try:
                if not is_dashboard_active_tender(
                    state=secop_tender.state,
                    apertura_estado=secop_tender.apertura_estado,
                ):
                    continue

                if secop_tender.external_id in existing_ids:
                    existing = (
                        db.query(Tender)
                        .filter(Tender.external_id == secop_tender.external_id)
                        .first()
                    )
                    if existing:
                        _apply_secop_fields(existing, secop_tender)
                        updated_count += 1
                    continue

                new_tender = _tender_from_secop(secop_tender)
                db.add(new_tender)
                new_tenders.append(new_tender)
            except Exception as exc:
                logger.error(
                    "Error processing tender %s: %s",
                    secop_tender.external_id,
                    exc,
                )

        try:
            db.commit()
        except Exception as exc:
            logger.error("Error committing batch: %s", exc)
            db.rollback()

    return new_tenders, updated_count


def refresh_stale_tender_states(db: Session) -> dict[str, int]:
    """
    Re-fetch SECOP metadata for tenders already stored (any estado).

    Rotates through the catalogue by oldest updated_at so every tender is
    refreshed over time without a single heavy API call.
    """
    if not settings.SECOP_STATE_REFRESH_ENABLED:
        return {"candidates": 0, "refreshed": 0, "state_changes": 0}

    batch_size = settings.SECOP_STATE_REFRESH_BATCH_SIZE
    stale_tenders = (
        db.query(Tender)
        .order_by(Tender.updated_at.asc())
        .limit(batch_size)
        .all()
    )
    if not stale_tenders:
        return {"candidates": 0, "refreshed": 0, "state_changes": 0}

    by_external_id = {tender.external_id: tender for tender in stale_tenders}
    refreshed_dtos = fetch_tenders_by_external_ids(list(by_external_id.keys()))

    state_changes = 0
    refreshed = 0
    purged = 0
    for dto in refreshed_dtos:
        existing = by_external_id.get(dto.external_id)
        if not existing:
            continue
        previous_state = existing.state
        previous_apertura = existing.apertura_estado
        _apply_secop_fields(existing, dto)
        if not is_dashboard_active_tender(
            state=existing.state,
            apertura_estado=existing.apertura_estado,
        ):
            purge_tender(db, existing)
            purged += 1
            continue
        refreshed += 1
        if previous_state != dto.state or previous_apertura != dto.apertura_estado:
            state_changes += 1

    if refreshed or purged:
        db.commit()

    logger.info(
        "SECOP state refresh: candidates=%s refreshed=%s state_changes=%s purged=%s",
        len(stale_tenders),
        refreshed,
        state_changes,
        purged,
    )
    return {
        "candidates": len(stale_tenders),
        "refreshed": refreshed,
        "state_changes": state_changes,
        "purged": purged,
    }


def fetch_and_store_new_tenders(lookback_days: Optional[int] = None) -> None:
    """
    Main background job: fetch MVP-filtered SECOP tenders and persist them.

    User story 1.1:
    - Concurso de méritos abierto + UNSPSC + estado Publicado
    - Licitación pública Obra Publica + estado Publicado
    """
    db = SessionLocal()
    try:
        logger.info("=" * 60)
        logger.info("STARTING MVP SECOP TENDER FETCH JOB")
        logger.info("=" * 60)

        lookback = lookback_days if lookback_days is not None else settings.SECOP_FETCH_LOOKBACK_DAYS
        since_timestamp = datetime.utcnow() - timedelta(days=lookback)
        logger.info(
            "Fetching tenders published in the last %s day(s) (since %s)",
            lookback,
            since_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        )

        secop_tenders = fetch_mvp_secop_tenders(since_timestamp=since_timestamp)
        logger.info("Total unique MVP tenders found: %s", len(secop_tenders))

        new_tenders, updated_count = _persist_secop_batch(db, secop_tenders)
        logger.info(
            "Stored %s new tenders, updated %s existing from MVP fetch",
            len(new_tenders),
            updated_count,
        )

        refresh_stats = refresh_stale_tender_states(db)
        logger.info("SECOP state refresh stats: %s", refresh_stats)

        purge_stats = {"purged": 0}
        while True:
            batch_stats = purge_inactive_tenders(
                db,
                batch_size=settings.INACTIVE_TENDER_PURGE_BATCH_SIZE,
            )
            purge_stats["purged"] += batch_stats["purged"]
            if batch_stats["purged"] == 0:
                break
        logger.info("Inactive tender purge stats: %s", purge_stats)

        logger.info(
            "Next fetch scheduled in %s hours",
            settings.FETCH_INTERVAL_HOURS,
        )
        logger.info("=" * 60)

        doc_stats = extract_documents_for_pending_tenders(db)
        logger.info(
            "Document extraction: %s tenders processed, %s files saved",
            doc_stats["tenders_processed"],
            doc_stats["documents_saved"],
        )

        for tender in new_tenders:
            try:
                subscriptions = db.query(Subscription).filter(
                    Subscription.active == True
                ).all()

                for subscription in subscriptions:
                    if subscription.min_amount and tender.amount:
                        if tender.amount < subscription.min_amount:
                            continue

                    if subscription.max_amount and tender.amount:
                        if tender.amount > subscription.max_amount:
                            continue

                    if subscription.departments:
                        if tender.department not in subscription.departments:
                            continue

                    send_email_alert(subscription, tender)
                    send_whatsapp_alert(subscription, tender)
            except Exception as e:
                logger.error("Error sending notifications for tender %s: %s", tender.id, e)

        logger.info("MVP SECOP tender fetch job completed successfully")

    except Exception as e:
        logger.error("ERROR in fetch_and_store_new_tenders: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
