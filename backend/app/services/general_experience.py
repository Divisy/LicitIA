"""Store the pliego's general experience for active tenders, without the full requirements pass."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_requirements import TenderRequirements
from app.services.document_extraction import deduplicate_visible_documents
from app.services.secop_documents import is_archive_filename
from app.services.tender_lifecycle import filter_active_dashboard_tenders
from app.services.tender_requirements.document_selection import select_pliego_document
from app.services.tender_requirements.regex_extraction import extract_experiencia_general

logger = get_logger(__name__)

GENERAL_EXPERIENCE_VERSION = "general-1"
BATCH_LIMIT = 12


class _StoredPliego:
    def __init__(self, document: TenderDocument):
        self.id = document.id
        self.extension = document.extension
        self.file_name = document.file_name
        self.file_path = document.file_path


def general_experience_is_saved(payload: Optional[dict]) -> bool:
    """True when this tender already has a general-experience read or a full requirements extract."""
    if not payload:
        return False
    if payload.get("general_experience_extracted"):
        return True
    version = str(payload.get("extraction_version") or "")
    if not version or version.startswith("general-"):
        return False
    return any(
        section.get("key") == "experiencia_general"
        for section in payload.get("sections") or []
    )


def build_general_experience_payload(
    tender: Tender,
    items: list[dict],
    warning: Optional[str] = None,
) -> dict:
    return {
        "tender_external_id": tender.external_id,
        "extraction_version": GENERAL_EXPERIENCE_VERSION,
        "general_experience_extracted": True,
        "extracted_at": datetime.utcnow().isoformat(),
        "sections": [
            {
                "key": "experiencia_general",
                "title": "Experiencia general",
                "status": "encontrado" if items else "no_encontrado",
                "items": items,
            }
        ],
        "warnings": [warning] if warning else [],
    }


def _pliego_document(db: Session, tender_id) -> Optional[TenderDocument]:
    documents = (
        db.query(TenderDocument).filter(TenderDocument.tender_id == tender_id).all()
    )
    visible = [
        document
        for document in documents
        if not is_archive_filename(document.file_name)
    ]
    visible = deduplicate_visible_documents(visible)
    selected = select_pliego_document(visible)
    if selected is not None:
        return selected
    return next(
        (document for document in visible if document.document_type == "pliego_condiciones"),
        None,
    )


def _read_pliego_text(pliego: _StoredPliego) -> str:
    from app.services.document_storage import get_document_storage
    from app.services.tender_summary.pdf_text import extract_pdf_text

    return extract_pdf_text(pliego, get_document_storage())


def store_general_experience(
    db: Session,
    tender: Tender,
    items: list[dict],
    warning: Optional[str] = None,
) -> bool:
    record = (
        db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id == tender.id)
        .first()
    )
    if record and general_experience_is_saved(record.requirements_json):
        return False
    payload = build_general_experience_payload(tender, items, warning)
    if record is None:
        record = TenderRequirements(tender_id=tender.id)
        db.add(record)
    record.extraction_version = GENERAL_EXPERIENCE_VERSION
    record.requirements_json = payload
    record.extracted_at = datetime.utcnow()
    return True


def extract_general_experience_batch(db: Session, limit: int = BATCH_LIMIT) -> int:
    """Read stored pliegos of active tenders and save only the general-experience section."""
    pliego_ids = (
        db.query(TenderDocument.tender_id)
        .filter(TenderDocument.document_type == "pliego_condiciones")
        .distinct()
    )
    tenders = filter_active_dashboard_tenders(db.query(Tender)).filter(Tender.id.in_(pliego_ids)).all()
    if not tenders:
        db.commit()
        return 0
    stored = {
        row.tender_id: row.requirements_json
        for row in db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id.in_([tender.id for tender in tenders]))
        .all()
    }
    pending_ids = []
    for tender in tenders:
        if general_experience_is_saved(stored.get(tender.id)):
            continue
        pending_ids.append(tender.id)
        if len(pending_ids) >= limit:
            break
    db.commit()

    written = 0
    for tender_id in pending_ids:
        try:
            tender = db.query(Tender).filter(Tender.id == tender_id).first()
            pliego = _pliego_document(db, tender_id) if tender is not None else None
            if tender is None or pliego is None:
                db.commit()
                continue
            snapshot = _StoredPliego(pliego)
            external_id = tender.external_id
            db.commit()
            text = _read_pliego_text(snapshot)
            warning = None
            items: list[dict] = []
            if text.strip():
                items = extract_experiencia_general(text, "pliego_condiciones", snapshot.id)
            else:
                warning = "No se pudo leer texto del pliego"
            tender = db.query(Tender).filter(Tender.id == tender_id).one()
            store_general_experience(db, tender, items, warning)
            db.commit()
            written += 1
            logger.info(
                "Saved general experience for %s (%s items)",
                external_id,
                len(items),
            )
        except Exception:
            db.rollback()
            logger.exception("General experience failed for tender %s", tender_id)
    return written


def run_general_experience_job() -> None:
    """Background entry point. Reads a bounded batch and releases the database between pliegos."""
    db = SessionLocal()
    try:
        written = extract_general_experience_batch(db)
        logger.info("General experience batch saved %s tenders", written)
    except Exception:
        db.rollback()
        logger.exception("General experience batch failed")
    finally:
        db.close()
