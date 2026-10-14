"""Store the pliego's general experience for active tenders, without the full requirements pass."""
from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_requirements import TenderRequirements
from app.services.document_extraction import deduplicate_visible_documents
from app.services.secop_documents import is_archive_filename
from app.services.tender_lifecycle import filter_active_dashboard_tenders
from app.services.tender_requirements.document_selection import select_pliego_document
from app.services.tender_requirements.llm_extraction import extract_general_experience_with_llm
from app.services.tender_requirements.regex_extraction import (
    _general_experience_region,
    _item,
    extract_experiencia_general,
    normalize_text,
)
from app.services.tender_requirements.text_selection import select_experience_text_for_llm

logger = get_logger(__name__)

GENERAL_EXPERIENCE_VERSION = "general-1"
GENERAL_EXPERIENCE_LLM_VERSION = "general-llm-1"
BATCH_LIMIT = 12
_UNREADABLE_WARNING = "No se pudo leer texto del pliego"
_job_lock = threading.Lock()


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


def general_experience_llm_is_saved(payload: Optional[dict]) -> bool:
    """True only after the focused general-experience reading, not after the full pliego extract."""
    if not payload:
        return False
    return payload.get("general_experience_llm") is True


def _section(items: list[dict]) -> dict:
    return {
        "key": "experiencia_general",
        "title": "Experiencia general",
        "status": "extraido" if items else "no_encontrado",
        "items": items,
    }


def focused_general_experience_section(
    text: str,
    tender_external_id: str,
    source_document_id,
) -> Optional[dict]:
    """The background reading. None means the model call failed and the caller should retry."""
    if not (text or "").strip():
        return None
    excerpt = general_experience_excerpt(text)
    if not excerpt.strip():
        return None
    fields = extract_general_experience_with_llm(
        tender_external_id=tender_external_id,
        excerpt=excerpt,
    )
    if fields is None:
        return None
    return _section(general_experience_items_from_fields(fields, source_document_id))


def _general_experience_section(payload: Optional[dict]) -> Optional[dict]:
    if not payload:
        return None
    return next(
        (
            section
            for section in payload.get("sections") or []
            if section.get("key") == "experiencia_general"
        ),
        None,
    )


def apply_focused_general_experience_section(payload: dict, section: dict) -> dict:
    """Keep every other section. Experiencia general becomes the focused reading."""
    updated = deepcopy(payload)
    stored = deepcopy(section)
    stored["key"] = "experiencia_general"
    stored.setdefault("title", "Experiencia general")
    if stored.get("status") == "encontrado":
        stored["status"] = "extraido"
    sections = []
    replaced = False
    for current in updated.get("sections") or []:
        if current.get("key") == "experiencia_general":
            sections.append(stored)
            replaced = True
        else:
            sections.append(current)
    if not replaced:
        sections.append(stored)
    updated["sections"] = sections
    updated["general_experience_llm"] = True
    return updated


def replace_general_experience_with_focused_reading(
    payload: dict,
    *,
    text: str,
    tender_external_id: str,
    source_document_id,
    saved_section: Optional[dict] = None,
) -> dict:
    section = saved_section
    if section is None:
        section = focused_general_experience_section(text, tender_external_id, source_document_id)
    if section is None:
        return payload
    return apply_focused_general_experience_section(payload, section)


def refresh_focused_general_experience(db: Session, tender: Tender, payload: dict) -> dict:
    """Patch a full extract in place. The database is free while the pliego is read."""
    if general_experience_llm_is_saved(payload):
        return payload
    pliego = _pliego_document(db, tender.id)
    if pliego is None:
        return payload
    snapshot = _StoredPliego(pliego)
    external_id = tender.external_id
    db.commit()
    text = _read_pliego_text(snapshot)
    section = focused_general_experience_section(text, external_id, snapshot.id)
    if section is None:
        return payload
    return apply_focused_general_experience_section(payload, section)


def _is_full_extract(payload: Optional[dict]) -> bool:
    version = str((payload or {}).get("extraction_version") or "")
    return bool(version) and not version.startswith("general-")


def merge_general_experience_reading(
    existing: Optional[dict],
    *,
    tender_external_id: str,
    items: list[dict],
    llm_done: bool,
    warning: Optional[str] = None,
) -> dict:
    """Write the general-experience section. A full extract keeps its other sections and version."""
    if _is_full_extract(existing) and existing is not None:
        updated = deepcopy(existing)
        if llm_done:
            updated["general_experience_llm"] = True
        sections = []
        replaced = False
        section = _section(items)
        for current in updated.get("sections") or []:
            if current.get("key") == "experiencia_general":
                sections.append(section)
                replaced = True
            else:
                sections.append(current)
        if not replaced:
            sections.append(section)
        updated["sections"] = sections
        if warning:
            warnings = list(updated.get("warnings") or [])
            if warning not in warnings:
                warnings.append(warning)
            updated["warnings"] = warnings
        return updated

    payload = {
        "tender_external_id": tender_external_id,
        "extraction_version": GENERAL_EXPERIENCE_LLM_VERSION if llm_done else GENERAL_EXPERIENCE_VERSION,
        "general_experience_extracted": True,
        "extracted_at": datetime.utcnow().isoformat(),
        "sections": [_section(items)],
        "warnings": [warning] if warning else [],
    }
    if llm_done:
        payload["general_experience_llm"] = True
    return payload


def mark_general_experience_unreadable(
    existing: Optional[dict],
    tender_external_id: str,
) -> dict:
    """No selectable text. Keep a full extract's items and do not call the model again."""
    if _is_full_extract(existing) and existing is not None:
        updated = deepcopy(existing)
        updated["general_experience_llm"] = True
        warnings = list(updated.get("warnings") or [])
        if _UNREADABLE_WARNING not in warnings:
            warnings.append(_UNREADABLE_WARNING)
        updated["warnings"] = warnings
        return updated
    items: list[dict] = []
    if existing:
        section = next(
            (
                item
                for item in existing.get("sections") or []
                if item.get("key") == "experiencia_general"
            ),
            None,
        )
        items = list((section or {}).get("items") or [])
    return merge_general_experience_reading(
        existing,
        tender_external_id=tender_external_id,
        items=items,
        llm_done=True,
        warning=_UNREADABLE_WARNING,
    )


def general_experience_items_from_fields(
    fields: dict,
    source_document_id,
) -> list[dict]:
    """Turn a validated model payload into the items the SMMLV match already reads."""
    evidence = fields.get("evidence") if isinstance(fields.get("evidence"), dict) else {}
    items: list[dict] = []

    description = fields.get("requirement_description")
    if isinstance(description, str) and description.strip():
        items.append(
            _llm_item(
                key="requirement_description",
                label="Descripción del requisito",
                value=description,
                display_value=description,
                source_document_id=source_document_id,
                evidence=evidence.get("requirement_description") or description[:200],
            )
        )

    percentage = fields.get("min_percentage_budget")
    if isinstance(percentage, (int, float)) and not isinstance(percentage, bool):
        items.append(
            _llm_item(
                key="min_percentage_budget",
                label="Porcentaje mínimo del presupuesto",
                value=percentage,
                display_value=f"{percentage:g}% del Presupuesto Oficial",
                source_document_id=source_document_id,
                evidence=evidence.get("min_percentage_budget") or "",
            )
        )

    amount = fields.get("min_amount_smmlv")
    if isinstance(amount, (int, float)) and not isinstance(amount, bool):
        items.append(
            _llm_item(
                key="min_amount_smmlv",
                label="Monto mínimo en SMMLV",
                value=amount,
                display_value=f"{amount:g} SMMLV",
                source_document_id=source_document_id,
                evidence=evidence.get("min_amount_smmlv") or "",
            )
        )

    years = fields.get("time_window_years")
    if isinstance(years, int) and not isinstance(years, bool):
        items.append(
            _llm_item(
                key="time_window_years",
                label="Ventana temporal de experiencia",
                value=years,
                display_value=f"Últimos {years} años",
                source_document_id=source_document_id,
                evidence=evidence.get("time_window_years") or "",
            )
        )

    contracts = fields.get("contracts_minimum")
    if isinstance(contracts, dict) and contracts.get("minimum"):
        minimum = int(contracts["minimum"])
        maximum = contracts.get("maximum")
        if maximum is None:
            display = f"Mínimo {minimum} contratos"
        else:
            display = f"Mínimo {minimum} y máximo {int(maximum)} contratos"
        items.append(
            _llm_item(
                key="contracts_minimum",
                label="Número de contratos",
                value=contracts,
                display_value=display,
                source_document_id=source_document_id,
                evidence=evidence.get("contracts_minimum") or "",
            )
        )

    tiers = fields.get("experience_value_tiers")
    if isinstance(tiers, list) and tiers:
        percentages = [f"{tier['percentage']:g}%" for tier in tiers if isinstance(tier, dict)]
        items.append(
            _llm_item(
                key="experience_value_tiers",
                label="Valor mínimo a certificar",
                value=tiers,
                display_value=f"Según nº de contratos: {' / '.join(percentages)} del PO (SMMLV)",
                source_document_id=source_document_id,
                evidence=evidence.get("experience_value_tiers") or "",
            )
        )
    return items


def _llm_item(**kwargs) -> dict:
    item = _item(
        source_document="pliego_condiciones",
        confidence=0.9,
        **kwargs,
    )
    item["extraction_method"] = "llm"
    return item


def payload_for_general_experience_reading(
    existing: Optional[dict],
    *,
    tender_external_id: str,
    text: str,
    llm_fields: Optional[dict],
    source_document_id,
) -> Optional[dict]:
    """None means the stored row stays as it is: the call failed and a regex read is already saved."""
    if not (text or "").strip():
        return mark_general_experience_unreadable(existing, tender_external_id)
    if llm_fields is None:
        if general_experience_is_saved(existing):
            return None
        items = extract_experiencia_general(text, "pliego_condiciones", source_document_id)
        return merge_general_experience_reading(
            existing,
            tender_external_id=tender_external_id,
            items=items,
            llm_done=False,
        )
    items = general_experience_items_from_fields(llm_fields, source_document_id)
    return merge_general_experience_reading(
        existing,
        tender_external_id=tender_external_id,
        items=items,
        llm_done=True,
    )


def general_experience_excerpt(text: str) -> str:
    """General-experience fragment, capped at the same size used by the requirements model."""
    max_chars = settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS
    normalized = normalize_text(text)
    region = _general_experience_region(normalized).strip()
    if region and region != normalized:
        return region[:max_chars]
    return select_experience_text_for_llm(None, text, "", max_chars)


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


def _stored_payload(db: Session, tender_id) -> Optional[dict]:
    record = (
        db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id == tender_id)
        .first()
    )
    if record is None or not record.requirements_json:
        return None
    return deepcopy(record.requirements_json)


def _persist(db: Session, tender: Tender, payload: dict) -> None:
    record = (
        db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id == tender.id)
        .first()
    )
    if record is None:
        record = TenderRequirements(tender_id=tender.id)
        db.add(record)
    record.requirements_json = payload
    record.extraction_version = str(payload.get("extraction_version") or GENERAL_EXPERIENCE_LLM_VERSION)
    record.extracted_at = datetime.utcnow()


def _pending_tender_ids(db: Session) -> list:
    pliego_ids = (
        db.query(TenderDocument.tender_id)
        .filter(TenderDocument.document_type == "pliego_condiciones")
        .distinct()
    )
    tenders = filter_active_dashboard_tenders(db.query(Tender)).filter(Tender.id.in_(pliego_ids)).all()
    if not tenders:
        return []
    stored = {
        row.tender_id: row.requirements_json
        for row in db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id.in_([tender.id for tender in tenders]))
        .all()
    }
    return [
        tender.id
        for tender in tenders
        if not general_experience_llm_is_saved(stored.get(tender.id))
    ]


def _read_one(db: Session, tender_id) -> str:
    """Read one stored pliego. Returns saved, failed, or skipped. The database is free during the model call."""
    try:
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        pliego = _pliego_document(db, tender_id) if tender is not None else None
        if tender is None or pliego is None:
            db.commit()
            return "skipped"
        existing = _stored_payload(db, tender_id)
        if general_experience_llm_is_saved(existing):
            db.commit()
            return "skipped"
        snapshot = _StoredPliego(pliego)
        external_id = tender.external_id
        source_document_id = snapshot.id
        db.commit()

        text = _read_pliego_text(snapshot)
        excerpt = general_experience_excerpt(text) if text.strip() else ""
        if not text.strip() or not excerpt.strip():
            tender = db.query(Tender).filter(Tender.id == tender_id).one()
            existing = _stored_payload(db, tender_id)
            _persist(db, tender, mark_general_experience_unreadable(existing, external_id))
            db.commit()
            logger.info("General experience has no selectable text for %s", external_id)
            return "saved"

        fields = extract_general_experience_with_llm(
            tender_external_id=external_id,
            excerpt=excerpt,
        )
        tender = db.query(Tender).filter(Tender.id == tender_id).one()
        existing = _stored_payload(db, tender_id)
        if general_experience_llm_is_saved(existing):
            db.commit()
            return "skipped"
        payload = payload_for_general_experience_reading(
            existing,
            tender_external_id=external_id,
            text=text,
            llm_fields=fields,
            source_document_id=source_document_id,
        )
        if payload is None:
            db.commit()
            logger.info("General experience call failed for %s; kept the previous read", external_id)
            return "failed"
        _persist(db, tender, payload)
        db.commit()
        saved_items = next(
            (
                section.get("items") or []
                for section in payload.get("sections") or []
                if section.get("key") == "experiencia_general"
            ),
            [],
        )
        logger.info(
            "Saved general experience for %s (%s items, llm=%s)",
            external_id,
            len(saved_items),
            bool(payload.get("general_experience_llm")),
        )
        if fields is None:
            return "failed"
        return "saved"
    except Exception:
        db.rollback()
        logger.exception("General experience failed for tender %s", tender_id)
        return "failed"


def _extract_limited(db: Session, limit: int) -> int:
    pending = _pending_tender_ids(db)[:limit]
    db.commit()
    written = 0
    for tender_id in pending:
        if _read_one(db, tender_id) == "saved":
            written += 1
    return written


def extract_general_experience_batch(db: Session, limit: int = BATCH_LIMIT) -> int:
    """Read a bounded batch. Skips the batch when the startup drain is already running."""
    if not _job_lock.acquire(blocking=False):
        logger.info("General experience batch skipped because another pass is running")
        return 0
    try:
        return _extract_limited(db, limit)
    finally:
        _job_lock.release()


def run_general_experience_job() -> None:
    """Retry calls that failed. New pliegos are also picked up here."""
    db = SessionLocal()
    try:
        written = extract_general_experience_batch(db)
        logger.info("General experience batch saved %s tenders", written)
    except Exception:
        db.rollback()
        logger.exception("General experience batch failed")
    finally:
        db.close()


def run_general_experience_drain() -> None:
    """Read every stored pliego that does not yet have an AI general-experience result, one at a time."""
    if not _job_lock.acquire(blocking=False):
        logger.info("General experience drain skipped because another pass is running")
        return
    db = SessionLocal()
    saved = 0
    deferred: set[Any] = set()
    try:
        while True:
            pending = [tender_id for tender_id in _pending_tender_ids(db) if tender_id not in deferred]
            db.commit()
            if not pending:
                break
            for tender_id in pending:
                outcome = _read_one(db, tender_id)
                if outcome == "saved":
                    saved += 1
                else:
                    deferred.add(tender_id)
        logger.info(
            "General experience drain saved %s tenders and left %s for a later retry",
            saved,
            len(deferred),
        )
    except Exception:
        db.rollback()
        logger.exception("General experience drain failed")
    finally:
        db.close()
        _job_lock.release()
