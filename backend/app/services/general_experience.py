"""Store the pliego's general experience for active tenders, without the full requirements pass."""
from __future__ import annotations

import tempfile
import threading
from copy import deepcopy
from pathlib import Path
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
from app.services.tender_requirements.llm_extraction import (
    extract_general_experience_from_page_images,
    extract_general_experience_with_llm,
)
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


def _section_has_time_window(payload: Optional[dict]) -> bool:
    for section in (payload or {}).get("sections") or []:
        if section.get("key") != "experiencia_general":
            continue
        return any(item.get("key") == "time_window_years" for item in section.get("items") or [])
    return False


_EXPERIENCE_SUBJECT_STEMS = (
    "construc",
    "intervent",
    "supervis",
    "estudio",
    "diseno",
    "obra",
    "edific",
    "mantenim",
    "adecuac",
    "consultor",
    "restaur",
    "paviment",
    "rehabilit",
    "ampliac",
    "reconstruc",
    "suministro",
    "instalac",
    "conservac",
    "remodel",
    "dragado",
    "alcantarill",
    "acueduct",
    "infraestruct",
    "vivienda",
    "puente",
)


def experience_subject_is_written(text: Optional[str]) -> bool:
    """The sentence says what the experience must be, not only how many contracts are allowed."""
    folded = normalize_text(text or "")
    return any(stem in folded for stem in _EXPERIENCE_SUBJECT_STEMS)


def _item_text(payload: Optional[dict], section_key: str, item_key: str) -> str:
    for section in (payload or {}).get("sections") or []:
        if section.get("key") != section_key:
            continue
        for item in section.get("items") or []:
            if item.get("key") == item_key:
                return str(item.get("value") or item.get("display_value") or "")
    return ""


def _section_marks_subject(payload: Optional[dict], section_key: str) -> bool:
    for section in (payload or {}).get("sections") or []:
        if section.get("key") == section_key and section.get("experience_subject") is True:
            return True
    return False


def general_experience_reading_is_final(payload: Optional[dict]) -> bool:
    """A page reading is kept once it carries the paragraph of what the experience must be."""
    if not general_experience_llm_is_saved(payload):
        return False
    source = (payload or {}).get("general_experience_source")
    if source == "no_pages":
        return True
    if source == "pages":
        if (payload or {}).get("general_experience_subject") is True or _section_marks_subject(
            payload, "experiencia_general"
        ):
            return True
        return experience_subject_is_written(
            _item_text(payload, "experiencia_general", "requirement_description")
        )
    return source == "vision" and not _section_has_time_window(payload)


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
    pliego: Optional[_StoredPliego] = None,
) -> Optional[dict]:
    """The background reading. None means the model call failed and the caller should retry."""
    fields, _source = _fields_for_general_experience(text, tender_external_id, pliego)
    if fields is None:
        return None
    return _section(general_experience_items_from_fields(fields, source_document_id))


def _fields_for_general_experience(
    text: str,
    tender_external_id: str,
    pliego: Optional[_StoredPliego],
) -> tuple[Optional[dict], str]:
    """Read the printed pages. The text layer is only the fallback when those pages are not found."""
    if pliego is not None:
        images = _render_general_experience_pages(pliego)
        if images:
            fields = extract_general_experience_from_page_images(
                tender_external_id=tender_external_id,
                page_images=images,
            )
            return fields, "pages" if fields is not None else "vision"
        logger.info(
            "General experience pages were not found for %s; using the text layer",
            tender_external_id,
        )
    excerpt = general_experience_excerpt(text) if (text or "").strip() else ""
    if not excerpt.strip():
        return None, "no_pages"
    return (
        extract_general_experience_with_llm(
            tender_external_id=tender_external_id,
            excerpt=excerpt,
        ),
        "no_pages",
    )


def _render_general_experience_pages(pliego: _StoredPliego, limit: int = 3) -> list[bytes]:
    """JPEG of the printed general-experience pages. Empty when the heading cannot be found."""
    import fitz

    from app.services.document_storage import get_document_storage

    storage = get_document_storage()
    local_path = storage.local_path(pliego.file_path)
    temp_dir = None
    if not local_path.is_file():
        temp_dir = tempfile.TemporaryDirectory(prefix="licitia_pdf_")
        local_path = Path(temp_dir.name) / Path(pliego.file_name or "pliego.pdf").name
        with local_path.open("wb") as handle:
            for chunk in storage.iter_file_chunks(pliego.file_path):
                handle.write(chunk)
    images: list[bytes] = []
    try:
        document = fitz.open(local_path)
        try:
            start = _general_experience_page_index(document)
            if start is None:
                return []
            for index in _printed_page_span(start, document.page_count, limit):
                pixmap = document[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(pixmap.tobytes("jpeg", jpg_quality=72))
        finally:
            document.close()
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
    return images


def _printed_page_span(start: int, page_count: int, limit: int) -> range:
    """The located page, the one before it, and the following ones, up to limit."""
    first = max(0, start - 1)
    return range(first, min(first + limit, page_count))


def _general_experience_page_index(document) -> Optional[int]:
    fallback = None
    for index, page in enumerate(document):
        normalized = normalize_text(page.get_text("text") or "")
        if "experiencia general" not in normalized:
            continue
        if fallback is None:
            fallback = index
        if "habilitante" in normalized or "acreditar" in normalized:
            return index
    return fallback


def finish_focused_reading(
    pliego: _StoredPliego,
    tender_external_id: str,
    existing: Optional[dict],
) -> Optional[dict]:
    """Read one pliego. None means the call failed and the stored row should stay as it is."""
    text = _read_pliego_text(pliego)
    fields, source = _fields_for_general_experience(text, tender_external_id, pliego)
    if fields is None:
        if source == "vision":
            return None
        if not (text or "").strip():
            payload = mark_general_experience_unreadable(existing, tender_external_id)
            payload["general_experience_source"] = "no_pages"
            return payload
        if general_experience_llm_is_saved(existing):
            return None
        return payload_for_general_experience_reading(
            existing,
            tender_external_id=tender_external_id,
            text=text,
            llm_fields=None,
            source_document_id=pliego.id,
        )
    section = _section(general_experience_items_from_fields(fields, pliego.id))
    if source == "pages":
        section["experience_subject"] = True
    if _is_full_extract(existing):
        return apply_focused_general_experience_section(existing, section, source)
    payload = merge_general_experience_reading(
        existing,
        tender_external_id=tender_external_id,
        items=section["items"],
        llm_done=True,
    )
    payload["general_experience_source"] = source
    if source == "pages":
        payload["general_experience_subject"] = True
        for stored in payload.get("sections") or []:
            if stored.get("key") == "experiencia_general":
                stored["experience_subject"] = True
    return payload


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


def apply_focused_general_experience_section(
    payload: dict,
    section: dict,
    source: str = "text",
) -> dict:
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
    updated["general_experience_source"] = source
    if stored.get("experience_subject") is True:
        updated["general_experience_subject"] = True
    return updated


def replace_general_experience_with_focused_reading(
    payload: dict,
    *,
    text: str,
    tender_external_id: str,
    source_document_id,
    saved_section: Optional[dict] = None,
    saved_source: Optional[str] = None,
    pliego: Optional[_StoredPliego] = None,
) -> dict:
    source = saved_source or "text"
    section = saved_section
    if section is None:
        fields, source = _fields_for_general_experience(text, tender_external_id, pliego)
        if fields is None:
            return payload
        section = _section(general_experience_items_from_fields(fields, source_document_id))
    return apply_focused_general_experience_section(payload, section, source)


def refresh_focused_general_experience(db: Session, tender: Tender, payload: dict) -> dict:
    """Patch a full extract in place. The database is free while the pliego is read."""
    if general_experience_reading_is_final(payload):
        return payload
    pliego = _pliego_document(db, tender.id)
    if pliego is None:
        return payload
    snapshot = _StoredPliego(pliego)
    external_id = tender.external_id
    db.commit()
    updated = finish_focused_reading(snapshot, external_id, payload)
    return payload if updated is None else updated


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
        payload["general_experience_source"] = "no_pages"
    return payload


def mark_general_experience_unreadable(
    existing: Optional[dict],
    tender_external_id: str,
) -> dict:
    """No selectable text. Keep a full extract's items and do not call the model again."""
    if _is_full_extract(existing) and existing is not None:
        updated = deepcopy(existing)
        updated["general_experience_llm"] = True
        updated["general_experience_source"] = "no_pages"
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
                display_value=f"Los contratos de la experiencia deben ser de los últimos {years} años",
                source_document_id=source_document_id,
                evidence=evidence.get("time_window_years") or "",
            )
        )

    duration = fields.get("company_duration")
    if isinstance(duration, str) and duration.strip():
        items.append(
            _llm_item(
                key="company_duration",
                label="Duración de la persona jurídica",
                value=duration,
                display_value=duration,
                source_document_id=source_document_id,
                evidence=evidence.get("company_duration") or duration[:200],
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


def _specific_reading_is_final(payload: Optional[dict]) -> bool:
    from app.services.pliego_specific_experience import specific_experience_reading_is_final

    return specific_experience_reading_is_final(payload)


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
        if not general_experience_reading_is_final(stored.get(tender.id))
        or not _specific_reading_is_final(stored.get(tender.id))
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
        if general_experience_reading_is_final(existing) and _specific_reading_is_final(existing):
            db.commit()
            return "skipped"
        snapshot = _StoredPliego(pliego)
        external_id = tender.external_id
        db.commit()

        tender = db.query(Tender).filter(Tender.id == tender_id).one()
        existing = _stored_payload(db, tender_id)
        if general_experience_reading_is_final(existing) and _specific_reading_is_final(existing):
            db.commit()
            return "skipped"
        payload = existing
        if not general_experience_reading_is_final(existing):
            payload = finish_focused_reading(snapshot, external_id, existing)
            if payload is None:
                db.commit()
                logger.info("General experience call failed for %s; kept the previous read", external_id)
                return "failed"
        if not _specific_reading_is_final(payload):
            from app.services.pliego_specific_experience import finish_specific_reading

            updated = finish_specific_reading(snapshot, external_id, payload)
            if updated is None:
                if payload is not existing:
                    _persist(db, tender, payload)
                    db.commit()
                else:
                    db.commit()
                logger.info("Specific experience call failed for %s; kept the previous read", external_id)
                return "failed"
            payload = updated
        _persist(db, tender, payload)
        db.commit()
        logger.info(
            "Saved pliego experience for %s (general=%s, specific=%s)",
            external_id,
            payload.get("general_experience_source"),
            payload.get("specific_experience_source"),
        )
        if not general_experience_llm_is_saved(payload):
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
