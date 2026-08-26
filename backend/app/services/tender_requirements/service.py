"""Build structured tender requirements payload (US 1.5)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_requirements import TenderRequirements
from app.services.document_extraction import deduplicate_visible_documents
from app.services.document_storage import get_document_storage
from app.services.secop_documents import is_archive_filename
from app.services.tender_requirements.document_selection import (
    select_anexo_document,
    select_pliego_document,
)
from app.services.tender_requirements.llm_extraction import enrich_requirements_with_llm
from app.services.tender_requirements.regex_extraction import EXTRACTORS, SECTION_DEFINITIONS, _merge_items
from app.services.tender_requirements.pdf_pages import extract_pdf_pages, join_pages
from app.services.tender_requirements.text_selection import (
    prepare_pliego_requirement_text,
    select_requirement_relevant_text,
)
from app.services.tender_summary.pdf_text import extract_pdf_text

EXTRACTION_VERSION = "1.5.2"

_SECTION_SOURCE = {key: source for key, _, source in SECTION_DEFINITIONS}
_SECTION_TITLE = {key: title for key, title, _ in SECTION_DEFINITIONS}


def _visible_documents(tender: Tender) -> list[TenderDocument]:
    documents = [
        document
        for document in tender.documents
        if not is_archive_filename(document.file_name)
    ]
    return deduplicate_visible_documents(documents)


def _prepare_anexo_text(raw_text: str) -> str:
    return select_requirement_relevant_text(
        raw_text,
        settings.TENDER_REQUIREMENTS_MAX_CHARS,
    )


def _section_status(
    section_key: str,
    items: list[dict[str, Any]],
    *,
    has_source_document: bool,
    text_extracted: bool,
) -> str:
    if not has_source_document:
        return "documento_no_disponible"
    if not text_extracted:
        return "no_extraible"
    if items:
        low_confidence = any(item.get("confidence", 1) < 0.75 for item in items)
        return "revisar" if low_confidence else "extraido"
    return "no_encontrado"


def build_tender_requirements(tender: Tender) -> dict[str, Any]:
    """Extract participation requirements from pliego and anexo documents."""
    if not settings.TENDER_REQUIREMENTS_EXTRACTION_ENABLED:
        return {
            "tender_external_id": tender.external_id,
            "extraction_version": EXTRACTION_VERSION,
            "extracted_at": datetime.utcnow().isoformat(),
            "sections": [],
            "warnings": ["Tender requirements extraction is disabled"],
        }

    documents = _visible_documents(tender)
    pliego = select_pliego_document(documents)
    anexo = select_anexo_document(documents)
    storage = get_document_storage()

    pliego_text = ""
    anexo_text = ""
    warnings: list[str] = []

    if pliego:
        pliego_pages = extract_pdf_pages(pliego, storage)
        pliego_raw = join_pages(pliego_pages) or extract_pdf_text(pliego, storage)
        pliego_text, pliego_notes = prepare_pliego_requirement_text(
            pliego_pages,
            pliego_raw,
            settings.TENDER_REQUIREMENTS_MAX_CHARS,
        )
        warnings.extend(pliego_notes)
        if not pliego_text.strip():
            warnings.append(f"No se pudo extraer texto del pliego ({pliego.file_name})")
    if anexo:
        extension = (anexo.extension or "").lower()
        if extension == "docx":
            warnings.append(
                f"El anexo ({anexo.file_name}) es DOCX; la experiencia específica se extrae del pliego cuando aplique"
            )
        else:
            anexo_text = _prepare_anexo_text(extract_pdf_text(anexo, storage))
            if not anexo_text.strip():
                warnings.append(f"No se pudo extraer texto del anexo ({anexo.file_name})")

    if not pliego and not anexo:
        warnings.append("Sube el pliego o el anexo técnico para extraer requisitos")

    extracted_by_section: dict[str, list[dict[str, Any]]] = {}

    for section_key, _, default_source in SECTION_DEFINITIONS:
        if section_key == "experiencia_especifica":
            items: list[dict[str, Any]] = []
            if pliego_text.strip():
                items = _merge_items(
                    items,
                    EXTRACTORS[section_key](
                        pliego_text,
                        pliego.document_type if pliego else "pliego_condiciones",
                        pliego.id if pliego else None,
                    ),
                )
            if anexo_text.strip():
                items = _merge_items(
                    items,
                    EXTRACTORS[section_key](
                        anexo_text,
                        anexo.document_type if anexo else "anexo_tecnico",
                        anexo.id if anexo else None,
                    ),
                )
            extracted_by_section[section_key] = items
            continue

        if section_key == "otros":
            document = pliego or anexo
            text = pliego_text or anexo_text
        else:
            document = pliego
            text = pliego_text

        extractor = EXTRACTORS[section_key]
        source_document_id = document.id if document else None
        effective_source = document.document_type if document else default_source
        extracted_by_section[section_key] = extractor(
            text,
            effective_source,
            source_document_id,
        )

    extracted_by_section = enrich_requirements_with_llm(
        tender_external_id=tender.external_id,
        object_text=tender.object_text,
        pliego_excerpt=pliego_text,
        anexo_excerpt=anexo_text,
        existing_sections=extracted_by_section,
    )

    sections: list[dict[str, Any]] = []
    for section_key, title, default_source in SECTION_DEFINITIONS:
        if section_key == "experiencia_especifica":
            has_source_document = pliego is not None or anexo is not None
            text_extracted = bool(pliego_text.strip() or anexo_text.strip())
        elif section_key == "otros":
            has_source_document = pliego is not None or anexo is not None
            text_extracted = bool((pliego_text or anexo_text).strip())
        else:
            has_source_document = pliego is not None
            text_extracted = bool(pliego_text.strip())

        items = extracted_by_section.get(section_key, [])
        sections.append(
            {
                "key": section_key,
                "title": title,
                "status": _section_status(
                    section_key,
                    items,
                    has_source_document=has_source_document,
                    text_extracted=text_extracted,
                ),
                "items": items,
            }
        )

    return {
        "tender_external_id": tender.external_id,
        "extraction_version": EXTRACTION_VERSION,
        "extracted_at": datetime.utcnow().isoformat(),
        "sections": sections,
        "warnings": warnings,
    }


def persist_tender_requirements(
    db: Session,
    tender: Tender,
    payload: dict[str, Any],
) -> TenderRequirements:
    record = (
        db.query(TenderRequirements)
        .filter(TenderRequirements.tender_id == tender.id)
        .first()
    )
    if not record:
        record = TenderRequirements(tender_id=tender.id)

    record.extraction_version = payload.get("extraction_version", EXTRACTION_VERSION)
    record.requirements_json = payload
    record.extracted_at = datetime.utcnow()
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
