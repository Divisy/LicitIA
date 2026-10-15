"""Copy the pliego's printed specific-experience section from its page."""
from __future__ import annotations

import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.tender import Tender
from app.services.general_experience import (
    _StoredPliego,
    _llm_item,
    _printed_page_span,
    experience_subject_is_written,
)
from app.services.tender_requirements.llm_extraction import extract_specific_experience_from_page_images
from app.services.tender_requirements.regex_extraction import normalize_text

logger = get_logger(__name__)


def specific_experience_reading_is_final(payload: Optional[dict]) -> bool:
    """A page reading is kept once it carries the paragraph of what the specific experience must be."""
    if not payload or payload.get("specific_experience_llm") is not True:
        return False
    source = payload.get("specific_experience_source")
    if source == "no_pages":
        return True
    if source != "pages":
        return False
    if payload.get("specific_experience_subject") is True:
        return True
    for section in payload.get("sections") or []:
        if section.get("key") != "experiencia_especifica":
            continue
        if section.get("experience_subject") is True:
            return True
        for item in section.get("items") or []:
            if item.get("key") == "specific_scope" and experience_subject_is_written(
                str(item.get("value") or "")
            ):
                return True
    return False


def _specific_section(items: list[dict]) -> dict:
    return {
        "key": "experiencia_especifica",
        "title": "Experiencia específica",
        "status": "extraido" if items else "no_encontrado",
        "items": items,
    }


def specific_experience_items_from_fields(fields: dict, source_document_id) -> list[dict]:
    evidence = fields.get("evidence") if isinstance(fields.get("evidence"), dict) else {}
    items: list[dict] = []

    scope = fields.get("specific_scope")
    if isinstance(scope, str) and scope.strip():
        items.append(
            _llm_item(
                key="specific_scope",
                label="Alcance exigido",
                value=scope,
                display_value=scope,
                source_document_id=source_document_id,
                evidence=evidence.get("specific_scope") or scope[:200],
            )
        )

    percentage = fields.get("specific_min_percentage")
    if isinstance(percentage, (int, float)) and not isinstance(percentage, bool):
        items.append(
            _llm_item(
                key="specific_min_percentage",
                label="Porcentaje mínimo específico",
                value=percentage,
                display_value=f"{percentage:g}% del Presupuesto Oficial",
                source_document_id=source_document_id,
                evidence=evidence.get("specific_min_percentage") or "",
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

    contracts = fields.get("contracts_minimum")
    if isinstance(contracts, dict) and contracts.get("minimum"):
        minimum = int(contracts["minimum"])
        maximum = contracts.get("maximum")
        display = (
            f"Mínimo {minimum} contratos"
            if maximum is None
            else f"Mínimo {minimum} y máximo {int(maximum)} contratos"
        )
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
    return items


def _specific_page_index(document) -> Optional[int]:
    fallback = None
    for index, page in enumerate(document):
        normalized = normalize_text(page.get_text("text") or "")
        if "experiencia especifica" not in normalized:
            continue
        if fallback is None:
            fallback = index
        if "habilitante" in normalized or "acreditar" in normalized:
            return index
    return fallback


def _render_specific_experience_pages(pliego: _StoredPliego) -> list[bytes]:
    """The heading page and the next one, so a section that starts at the bottom is not cut."""
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
            start = _specific_page_index(document)
            if start is None:
                return []
            for index in _printed_page_span(start, document.page_count, 3):
                pixmap = document[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(pixmap.tobytes("jpeg", jpg_quality=72))
        finally:
            document.close()
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()
    return images


def apply_focused_specific_experience_section(payload: dict, section: dict, source: str) -> dict:
    """Keep every other section. Experiencia específica becomes the printed-page reading."""
    updated = deepcopy(payload)
    stored = deepcopy(section)
    stored["key"] = "experiencia_especifica"
    stored.setdefault("title", "Experiencia específica")
    sections = []
    replaced = False
    for current in updated.get("sections") or []:
        if current.get("key") == "experiencia_especifica":
            sections.append(stored)
            replaced = True
        else:
            sections.append(current)
    if not replaced:
        sections.append(stored)
    updated["sections"] = sections
    updated["specific_experience_llm"] = True
    updated["specific_experience_source"] = source
    if stored.get("experience_subject") is True:
        updated["specific_experience_subject"] = True
    return updated


def finish_specific_reading(
    pliego: _StoredPliego,
    tender_external_id: str,
    existing: Optional[dict],
) -> Optional[dict]:
    """None means the image call failed and the stored row should stay as it is."""
    images = _render_specific_experience_pages(pliego)
    if not images:
        logger.info("Specific experience page was not found for %s", tender_external_id)
        base = deepcopy(existing) if existing else {
            "tender_external_id": tender_external_id,
            "sections": [],
        }
        return apply_focused_specific_experience_section(base, _specific_section([]), "no_pages")
    fields = extract_specific_experience_from_page_images(
        tender_external_id=tender_external_id,
        page_images=images,
    )
    if fields is None:
        return None
    section = _specific_section(specific_experience_items_from_fields(fields, pliego.id))
    section["experience_subject"] = True
    base = existing or {"tender_external_id": tender_external_id, "sections": []}
    return apply_focused_specific_experience_section(base, section, "pages")


def replace_specific_experience_with_focused_reading(
    payload: dict,
    *,
    tender_external_id: str,
    saved_section: Optional[dict] = None,
    saved_source: Optional[str] = None,
    pliego: Optional[_StoredPliego] = None,
) -> dict:
    if saved_section is not None:
        return apply_focused_specific_experience_section(payload, saved_section, saved_source or "pages")
    if pliego is None:
        return payload
    updated = finish_specific_reading(pliego, tender_external_id, payload)
    return payload if updated is None else updated


def refresh_focused_specific_experience(db: Session, tender: Tender, payload: dict) -> dict:
    """Patch the specific section in place. The database is free while the page is read."""
    if specific_experience_reading_is_final(payload):
        return payload
    from app.services.general_experience import _pliego_document

    pliego = _pliego_document(db, tender.id)
    if pliego is None:
        return payload
    snapshot = _StoredPliego(pliego)
    external_id = tender.external_id
    db.commit()
    updated = finish_specific_reading(snapshot, external_id, payload)
    return payload if updated is None else updated
