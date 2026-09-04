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
    select_indicadores_financieros_document,
    select_pliego_document,
)
from app.services.tender_requirements.scoring_extraction import (
    merge_scoring_fallback_items,
    reconcile_sistema_puntos_items,
    sistema_puntos_sum_mismatch,
)
from app.services.tender_requirements.llm_extraction import (
    enrich_requirements_with_llm,
    extract_scoring_fallback_with_llm,
    sanitize_experiencia_especifica_items,
)
from app.services.tender_requirements.regex_extraction import EXTRACTORS, SECTION_DEFINITIONS, _merge_items, merge_financial_requirement_items
from app.services.tender_requirements.pdf_pages import extract_pdf_pages, join_pages
from app.services.tender_requirements.text_selection import (
    prepare_pliego_requirement_text,
    select_experience_text_for_llm,
    select_financial_text_for_llm,
    select_legal_text_for_llm,
    select_scoring_text_for_llm,
    select_scoring_fallback_text_for_llm,
    select_requirement_relevant_text,
)
from app.services.document_text import extract_document_text
from app.services.tender_summary.contract_kind import ContractKind, detect_contract_kind
from app.services.tender_summary.pdf_text import extract_pdf_text

EXTRACTION_VERSION = "1.9.11"

_OBRA_RESIDUAL_CONTRACT_KINDS = frozenset(
    {ContractKind.EJECUCION_OBRA, ContractKind.ESTUDIOS_DISENOS_Y_OBRA}
)

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
    indicadores = select_indicadores_financieros_document(documents)
    storage = get_document_storage()

    pliego_text = ""
    pliego_raw = ""
    anexo_text = ""
    indicadores_text = ""
    indicadores_raw = ""
    pliego_pages: list[tuple[int, str]] = []
    indicadores_pages: list[tuple[int, str]] = []
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
    if indicadores:
        extension = (indicadores.extension or "").lower()
        if extension == "pdf":
            indicadores_pages = extract_pdf_pages(indicadores, storage)
            indicadores_raw = join_pages(indicadores_pages) or extract_document_text(
                indicadores, storage
            )
        else:
            indicadores_raw = extract_document_text(indicadores, storage)
        if indicadores_raw.strip():
            indicadores_text = indicadores_raw
        else:
            warnings.append(
                f"No se pudo extraer texto de indicadores financieros ({indicadores.file_name})"
            )
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
    contract_kind = detect_contract_kind(tender)

    for section_key, _, default_source in SECTION_DEFINITIONS:
        if section_key == "capacidad_residual":
            if contract_kind not in _OBRA_RESIDUAL_CONTRACT_KINDS:
                continue
            if pliego and (pliego_raw or pliego_text):
                extracted_by_section[section_key] = EXTRACTORS[section_key](
                    pliego_raw or pliego_text,
                    pliego.document_type,
                    pliego.id,
                )
            else:
                extracted_by_section[section_key] = []
            continue

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

        if section_key == "indicadores_financieros":
            matriz_items: list[dict[str, Any]] = []
            pliego_items: list[dict[str, Any]] = []
            if indicadores and indicadores_raw.strip():
                matriz_items = EXTRACTORS[section_key](
                    indicadores_raw,
                    "indicadores_financieros",
                    indicadores.id,
                )
            if pliego and (pliego_raw or pliego_text):
                pliego_items = EXTRACTORS[section_key](
                    pliego_raw or pliego_text,
                    pliego.document_type,
                    pliego.id,
                )
            extracted_by_section[section_key] = merge_financial_requirement_items(
                matriz_items,
                pliego_items,
                has_matriz_document=indicadores is not None,
            )
            continue

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

    llm_experience_context = select_experience_text_for_llm(
        pliego_pages or None,
        pliego_text,
        anexo_text,
        settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS,
    )
    llm_financial_context = select_financial_text_for_llm(
        indicadores_pages or pliego_pages or None,
        indicadores_raw or pliego_raw or pliego_text,
        settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS,
    )
    llm_legal_context = select_legal_text_for_llm(
        pliego_pages or None,
        pliego_raw or pliego_text,
        settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS,
    )
    llm_scoring_context = select_scoring_text_for_llm(
        pliego_pages or None,
        pliego_raw or pliego_text,
        settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS,
    )
    regex_scoring_items = list(extracted_by_section.get("sistema_puntos") or [])
    extracted_by_section = enrich_requirements_with_llm(
        tender_external_id=tender.external_id,
        object_text=tender.object_text or "",
        context_excerpt=llm_experience_context,
        financial_context_excerpt=llm_financial_context,
        scoring_context_excerpt=llm_scoring_context,
        legal_context_excerpt=llm_legal_context,
        existing_sections=extracted_by_section,
    )
    if extracted_by_section.get("sistema_puntos") or regex_scoring_items:
        scoring_items = reconcile_sistema_puntos_items(
            extracted_by_section.get("sistema_puntos") or [],
            regex_items=regex_scoring_items,
        )
        if (
            settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK
            and sistema_puntos_sum_mismatch(scoring_items)
            and (pliego_raw or pliego_text).strip()
        ):
            fallback_excerpt = select_scoring_fallback_text_for_llm(
                pliego_raw or pliego_text,
                settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK_MAX_CHARS,
            )
            fallback_items = extract_scoring_fallback_with_llm(
                tender_external_id=tender.external_id,
                object_text=tender.object_text or "",
                scoring_excerpt=fallback_excerpt,
            )
            if fallback_items:
                scoring_items = merge_scoring_fallback_items(scoring_items, fallback_items)
        extracted_by_section["sistema_puntos"] = scoring_items
    if extracted_by_section.get("experiencia_especifica"):
        extracted_by_section["experiencia_especifica"] = sanitize_experiencia_especifica_items(
            extracted_by_section["experiencia_especifica"]
        )

    sections: list[dict[str, Any]] = []
    for section_key, title, default_source in SECTION_DEFINITIONS:
        if section_key == "capacidad_residual" and contract_kind not in _OBRA_RESIDUAL_CONTRACT_KINDS:
            continue

        if section_key == "experiencia_especifica":
            has_source_document = pliego is not None or anexo is not None
            text_extracted = bool(pliego_text.strip() or anexo_text.strip())
        elif section_key == "indicadores_financieros":
            has_source_document = indicadores is not None or pliego is not None
            text_extracted = bool(
                (indicadores_raw or indicadores_text or pliego_raw or pliego_text).strip()
            )
        elif section_key == "capacidad_residual":
            has_source_document = pliego is not None
            text_extracted = bool((pliego_raw or pliego_text).strip())
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


_FINANCIAL_METRIC_ITEM_KEYS = frozenset(
    {
        "liquidez_corriente",
        "endeudamiento",
        "cobertura_intereses",
        "rentabilidad_patrimonio",
        "rentabilidad_activo",
        "patrimonio_minimo",
    }
)


def _scoring_section_sum_mismatch(cached_payload: dict[str, Any]) -> bool:
    scoring_section = next(
        (
            section
            for section in cached_payload.get("sections", [])
            if section.get("key") == "sistema_puntos"
        ),
        None,
    )
    if not scoring_section:
        return False

    return sistema_puntos_sum_mismatch(scoring_section.get("items", []))


def requirements_cache_is_stale(tender: Tender, cached_payload: dict[str, Any]) -> bool:
    """Invalidate cached requirements when scoring or financial data is inconsistent."""
    if _scoring_section_sum_mismatch(cached_payload):
        return True

    indicadores = select_indicadores_financieros_document(_visible_documents(tender))
    if not indicadores:
        return False

    financial_section = next(
        (
            section
            for section in cached_payload.get("sections", [])
            if section.get("key") == "indicadores_financieros"
        ),
        None,
    )
    if not financial_section:
        return True

    items = financial_section.get("items", [])
    uses_matriz = any(
        item.get("source_document") == "indicadores_financieros"
        and item.get("key") in _FINANCIAL_METRIC_ITEM_KEYS
        for item in items
    )
    has_placeholder = any(
        "umbrales segun matriz 2" in (item.get("display_value") or "").lower().replace("á", "a")
        or "umbrales segun matriz 2"
        in str((item.get("value") or {}).get("threshold_note") or "").lower().replace("á", "a")
        for item in items
        if item.get("key") in _FINANCIAL_METRIC_ITEM_KEYS
    )
    return has_placeholder or not uses_matriz


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
