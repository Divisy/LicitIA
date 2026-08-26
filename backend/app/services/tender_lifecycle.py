"""Helpers to keep only active SECOP opportunities in storage and API."""
from __future__ import annotations

from sqlalchemy.orm import Query, Session

from app.core.logging import get_logger
from app.models.tender import Tender
from app.services.document_storage import get_document_storage
from app.services.secop_filters import (
    ESTADO_APERTURA_ABIERTO,
    ESTADO_PUBLICADO,
    is_dashboard_active_tender,
)

logger = get_logger(__name__)


def filter_active_dashboard_tenders(query: Query) -> Query:
    """Restrict a query to Publicado + apertura Abierto."""
    return query.filter(
        Tender.state == ESTADO_PUBLICADO,
        Tender.apertura_estado == ESTADO_APERTURA_ABIERTO,
    )


def purge_tender(db: Session, tender: Tender) -> None:
    """Delete a tender, its related rows, and stored document blobs."""
    storage = get_document_storage()
    for document in list(tender.documents):
        if not document.file_path:
            continue
        try:
            storage.delete_object(document.file_path)
        except Exception as exc:
            logger.warning(
                "Failed to delete object %s for tender %s: %s",
                document.file_path,
                tender.external_id,
                exc,
            )
    db.delete(tender)


def purge_inactive_tenders(db: Session, *, batch_size: int = 100) -> dict[str, int]:
    """Remove tenders that are no longer Publicado with apertura Abierto."""
    inactive = (
        db.query(Tender)
        .filter(
            (Tender.state != ESTADO_PUBLICADO)
            | (Tender.apertura_estado != ESTADO_APERTURA_ABIERTO)
            | (Tender.apertura_estado.is_(None))
        )
        .limit(batch_size)
        .all()
    )
    purged = 0
    for tender in inactive:
        purge_tender(db, tender)
        purged += 1
    if purged:
        db.commit()
    logger.info("Purged %s inactive tenders from storage", purged)
    return {"candidates": len(inactive), "purged": purged}
