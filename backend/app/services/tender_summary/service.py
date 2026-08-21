"""Build structured tender summary payload (US 1.4)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.models.tender_document import TenderDocument
from app.models.tender_summary import TenderSummary
from app.services.document_extraction import deduplicate_visible_documents
from app.services.document_storage import get_document_storage
from app.services.secop_documents import is_archive_filename
from app.services.tender_summary.contract_kind import (
    ContractKind,
    aiu_applies,
    contract_kind_label,
    detect_contract_kind,
)
from app.services.tender_summary.document_selection import (
    select_pliego_document,
    select_presupuesto_document,
)
from app.services.tender_summary.pdf_text import extract_pdf_text
from app.services.tender_summary.pliego_extraction import extract_from_pliego_text
from app.services.tender_summary.presupuesto_extraction import extract_from_presupuesto_xlsx

FieldStatus = str  # available | not_applicable | unavailable


def _field(
    *,
    key: str,
    label: str,
    priority: str,
    source: str,
    status: FieldStatus,
    value: Any = None,
    display_value: Optional[str] = None,
    source_document_id: Optional[UUID] = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "priority": priority,
        "source": source,
        "status": status,
        "value": value,
        "display_value": display_value,
        "source_document_id": str(source_document_id) if source_document_id else None,
    }


def _format_currency(amount: Optional[float]) -> Optional[str]:
    if amount is None:
        return None
    return f"$ {amount:,.0f}".replace(",", ".")


def _format_date(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    return value.strftime("%d/%m/%Y")


def _visible_documents(tender: Tender) -> list[TenderDocument]:
    documents = [
        document
        for document in tender.documents
        if not is_archive_filename(document.file_name)
    ]
    return deduplicate_visible_documents(documents)


def _parse_duration_months(duration: Optional[str]) -> Optional[float]:
    if not duration:
        return None
    lowered = duration.lower()
    combo = re.search(r"(\d+(?:[.,]\d+)?)\s*meses?\s+y\s+(\d+(?:[.,]\d+)?)\s*d[ií]as?", lowered)
    if combo:
        months = float(combo.group(1).replace(",", "."))
        days = float(combo.group(2).replace(",", "."))
        return months + (days / 30.0)

    match = lowered.split()
    if len(match) < 2:
        return None
    try:
        amount = float(match[0].replace(",", "."))
    except ValueError:
        return None
    unit = match[1]
    if unit.startswith("mes"):
        return amount
    if unit.startswith("dia"):
        return amount / 30.0
    if unit.startswith("ano") or unit.startswith("año"):
        return amount * 12.0
    return None


def build_tender_summary(tender: Tender) -> dict[str, Any]:
    """Extract general tender information according to US 1.4 field map."""
    contract_kind = detect_contract_kind(tender)
    documents = _visible_documents(tender)
    pliego = select_pliego_document(documents)
    presupuesto = select_presupuesto_document(documents)
    storage = get_document_storage()

    pliego_data = extract_from_pliego_text(extract_pdf_text(pliego, storage)) if pliego else None
    presupuesto_data = (
        extract_from_presupuesto_xlsx(presupuesto, storage) if presupuesto else None
    )

    admin_location = ", ".join(
        part for part in (tender.department, tender.municipality) if part
    ) or None
    exact_location = admin_location

    total_cost = float(tender.amount) if tender.amount is not None else None
    if presupuesto_data and presupuesto_data.official_budget_total:
        total_cost = presupuesto_data.official_budget_total

    fields: list[dict[str, Any]] = []

    fields.append(
        _field(
            key="offer_submission_date",
            label="Fecha de presentación de la oferta",
            priority="P0",
            source="secop",
            status="available" if tender.closing_date else "unavailable",
            value=tender.closing_date.isoformat() if tender.closing_date else None,
            display_value=_format_date(tender.closing_date),
        )
    )
    fields.append(
        _field(
            key="work_description",
            label="Trabajo a realizar",
            priority="P0",
            source="secop",
            status="available" if tender.object_text else "unavailable",
            value=tender.object_text,
            display_value=tender.object_text,
        )
    )
    fields.append(
        _field(
            key="admin_location",
            label="Ubicación administrativa",
            priority="P0",
            source="secop",
            status="available" if admin_location else "unavailable",
            value=admin_location,
            display_value=admin_location,
        )
    )
    fields.append(
        _field(
            key="total_cost",
            label="Costo total de la obra",
            priority="P0",
            source="secop" if not (presupuesto_data and presupuesto_data.official_budget_total) else "presupuesto",
            status="available" if total_cost is not None else "unavailable",
            value=total_cost,
            display_value=_format_currency(total_cost),
            source_document_id=presupuesto.id if presupuesto_data and presupuesto_data.official_budget_total and presupuesto else None,
        )
    )

    if not aiu_applies(contract_kind):
        fields.append(
            _field(
                key="aiu_percentage",
                label="Porcentaje de AIU",
                priority="P0",
                source="presupuesto",
                status="not_applicable",
                display_value="No aplica (interventoría / estudios y diseños)",
            )
        )
    elif presupuesto_data and presupuesto_data.aiu_percentage is not None:
        fields.append(
            _field(
                key="aiu_percentage",
                label="Porcentaje de AIU",
                priority="P0",
                source="presupuesto",
                status="available",
                value=presupuesto_data.aiu_percentage,
                display_value=f"{presupuesto_data.aiu_percentage:.2f}%",
                source_document_id=presupuesto.id if presupuesto else None,
            )
        )
    else:
        fields.append(
            _field(
                key="aiu_percentage",
                label="Porcentaje de AIU",
                priority="P0",
                source="presupuesto",
                status="unavailable",
                display_value="No disponible",
                source_document_id=presupuesto.id if presupuesto else None,
            )
        )

    fields.extend(
        [
            _field(
                key="execution_duration",
                label="Duración de la obra",
                priority="P1",
                source="pliego",
                status="available" if pliego_data and pliego_data.execution_duration else "unavailable",
                value=pliego_data.execution_duration if pliego_data else None,
                display_value=pliego_data.execution_duration if pliego_data else None,
                source_document_id=pliego.id if pliego else None,
            ),
            _field(
                key="advance_payment_percentage",
                label="Porcentaje de anticipo",
                priority="P1",
                source="pliego",
                status="available"
                if pliego_data and pliego_data.advance_payment_percentage is not None
                else "unavailable",
                value=pliego_data.advance_payment_percentage if pliego_data else None,
                display_value=(
                    f"{pliego_data.advance_payment_percentage:.2f}%"
                    if pliego_data and pliego_data.advance_payment_percentage is not None
                    else None
                ),
                source_document_id=pliego.id if pliego else None,
            ),
            _field(
                key="payment_method",
                label="Forma de pago",
                priority="P1",
                source="pliego",
                status="available" if pliego_data and pliego_data.payment_method else "unavailable",
                value=pliego_data.payment_method if pliego_data else None,
                display_value=pliego_data.payment_method if pliego_data else None,
                source_document_id=pliego.id if pliego else None,
            ),
            _field(
                key="exact_location",
                label="Ubicación exacta",
                priority="P1",
                source="secop",
                status="available" if exact_location else "unavailable",
                value=exact_location,
                display_value=exact_location,
            ),
        ]
    )

    duration_months = _parse_duration_months(pliego_data.execution_duration if pliego_data else None)
    monthly_cost = None
    if total_cost is not None and duration_months and duration_months > 0:
        monthly_cost = round(total_cost / duration_months, 2)

    fields.extend(
        [
            _field(
                key="price_adjustment",
                label="Precios con ajuste",
                priority="P2",
                source="pliego",
                status="available" if pliego_data and pliego_data.price_adjustment else "unavailable",
                value=pliego_data.price_adjustment if pliego_data else None,
                display_value=pliego_data.price_adjustment if pliego_data else None,
                source_document_id=pliego.id if pliego else None,
            ),
            _field(
                key="lots_groups",
                label="Grupos o lotes",
                priority="P2",
                source="pliego",
                status="available" if pliego_data and pliego_data.lots_groups else "unavailable",
                value=pliego_data.lots_groups if pliego_data else None,
                display_value=pliego_data.lots_groups if pliego_data else None,
                source_document_id=pliego.id if pliego else None,
            ),
            _field(
                key="budget_contract_relation",
                label="Relación contrato vs presupuesto oficial",
                priority="P2",
                source="pliego_presupuesto",
                status="available"
                if (pliego_data and pliego_data.budget_contract_relation)
                or (presupuesto_data and presupuesto_data.budget_relation_note)
                else "unavailable",
                value=(
                    presupuesto_data.budget_relation_note
                    if presupuesto_data and presupuesto_data.budget_relation_note
                    else (pliego_data.budget_contract_relation if pliego_data else None)
                ),
                display_value=(
                    presupuesto_data.budget_relation_note
                    if presupuesto_data and presupuesto_data.budget_relation_note
                    else (pliego_data.budget_contract_relation if pliego_data else None)
                ),
                source_document_id=(presupuesto.id if presupuesto else None)
                or (pliego.id if pliego else None),
            ),
            _field(
                key="monthly_cost",
                label="Costo mensual estimado",
                priority="P2",
                source="computed",
                status="available" if monthly_cost is not None else "unavailable",
                value=monthly_cost,
                display_value=_format_currency(monthly_cost),
            ),
        ]
    )

    award_display = None
    if pliego_data and pliego_data.award_date:
        award_display = pliego_data.award_date
    fields.append(
        _field(
            key="award_date",
            label="Fecha de adjudicación",
            priority="P3",
            source="pliego" if award_display else "secop",
            status="available" if award_display else "unavailable",
            value=award_display,
            display_value=award_display,
            source_document_id=pliego.id if pliego and award_display else None,
        )
    )

    return {
        "tender_id": str(tender.id),
        "contract_kind": contract_kind.value,
        "contract_kind_label": contract_kind_label(contract_kind),
        "extracted_at": datetime.utcnow().isoformat(),
        "fields": fields,
    }


def persist_tender_summary(db: Session, tender: Tender, payload: dict[str, Any]) -> TenderSummary:
    record = db.query(TenderSummary).filter(TenderSummary.tender_id == tender.id).first()
    if record is None:
        record = TenderSummary(tender_id=tender.id)
        db.add(record)

    record.contract_kind = payload["contract_kind"]
    record.summary_json = payload
    record.extracted_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record
