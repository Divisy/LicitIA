"""Tender ingestion service - fetches, stores, classifies, and notifies."""
from datetime import datetime, timedelta
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.tender import Tender, TenderSource
from app.models.subscription import Subscription
from app.services.secop_client import SecopTenderDTO, fetch_mvp_secop_tenders
from app.config import settings
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


def fetch_and_store_new_tenders() -> None:
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

        since_timestamp = datetime.utcnow() - timedelta(days=settings.SECOP_FETCH_LOOKBACK_DAYS)
        logger.info(
            "Fetching tenders published in the last %s day(s) (since %s)",
            settings.SECOP_FETCH_LOOKBACK_DAYS,
            since_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        )

        secop_tenders = fetch_mvp_secop_tenders(since_timestamp=since_timestamp)
        logger.info("Total unique MVP tenders found: %s", len(secop_tenders))

        new_tenders = []
        updated_count = 0

        batch_size = 100
        for i in range(0, len(secop_tenders), batch_size):
            batch = secop_tenders[i:i + batch_size]

            batch_external_ids = [t.external_id for t in batch]
            existing_ids = set(
                row[0]
                for row in db.query(Tender.external_id)
                .filter(Tender.external_id.in_(batch_external_ids))
                .all()
            )

            for secop_tender in batch:
                try:
                    if secop_tender.external_id in existing_ids:
                        existing = db.query(Tender).filter(
                            Tender.external_id == secop_tender.external_id
                        ).first()
                        if existing:
                            _apply_secop_fields(existing, secop_tender)
                            updated_count += 1
                        continue

                    new_tender = _tender_from_secop(secop_tender)
                    db.add(new_tender)
                    new_tenders.append(new_tender)
                except Exception as e:
                    logger.error(
                        "Error processing tender %s: %s",
                        secop_tender.external_id,
                        e,
                    )
                    continue

            try:
                db.commit()
            except Exception as e:
                logger.error("Error committing batch: %s", e)
                db.rollback()

        logger.info(
            "Stored %s new tenders, updated %s existing",
            len(new_tenders),
            updated_count,
        )
        db.commit()

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
