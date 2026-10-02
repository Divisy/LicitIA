"""RUP certificate import API (US 1.11)."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import get_db
from app.core.logging import get_logger
from app.models.company_capacity import CompanyCapacity
from app.models.company_experience import CompanyExperience
from app.schemas.rup import RupCapacityPayload, RupImportResponse, RupProfileResponse
from app.services.document_storage import get_document_storage
from app.services.rup_import import persist_rup_pdf, replace_experiences_from_rup, upsert_capacity
from app.services.rup_parser import extract_text_from_pdf_bytes, parse_rup_text

logger = get_logger(__name__)
router = APIRouter()

_EXCEL_SUFFIXES = (".xlsx", ".xls")
_RUP_MAX_BYTES = min(getattr(settings, "RUP_UPLOAD_MAX_BYTES", 26_214_400), 26_214_400)


def _capacity_payload(row: Optional[CompanyCapacity]) -> RupCapacityPayload:
    if row is None:
        return RupCapacityPayload()
    organizational = None
    if row.organizational_json:
        try:
            organizational = json.loads(row.organizational_json)
        except json.JSONDecodeError:
            organizational = None
    return RupCapacityPayload(
        liquidez=float(row.liquidity) if row.liquidity is not None else None,
        endeudamiento=float(row.indebtedness) if row.indebtedness is not None else None,
        cobertura_intereses=float(row.interest_coverage) if row.interest_coverage is not None else None,
        rentabilidad_patrimonio=float(row.return_on_equity) if row.return_on_equity is not None else None,
        rentabilidad_activo=float(row.return_on_assets) if row.return_on_assets is not None else None,
        capital_trabajo=float(row.working_capital) if row.working_capital is not None else None,
        cut_year=row.cut_year,
        organizacional=organizational,
    )


def _warnings(row: Optional[CompanyCapacity]) -> list[str]:
    if not row or not row.warnings_json:
        return []
    try:
        parsed = json.loads(row.warnings_json)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


@router.post("/rup/import", response_model=RupImportResponse)
async def import_rup(
    file: UploadFile = File(..., description="Certificado RUP en PDF"),
    company_name: str = Query("Mi Empresa", min_length=1, description="Company name"),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "").strip()
    lowered = filename.lower()
    if lowered.endswith(_EXCEL_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="Sube el certificado RUP en PDF, no la plantilla de experiencias.",
        )
    if not lowered.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF del certificado RUP.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > _RUP_MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail="El PDF supera el tamaño máximo (25 MB). Sube el certificado descargado de la cámara.",
        )

    try:
        text = extract_text_from_pdf_bytes(content)
    except Exception as exc:
        logger.warning("Failed to read RUP PDF %s: %s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer el PDF. Sube el certificado RUP descargado de la cámara (texto seleccionable).",
        ) from exc

    parsed = parse_rup_text(text)
    if parsed.text_insufficient:
        raise HTTPException(
            status_code=400,
            detail="Este PDF parece escaneado; usa el certificado descargado de la cámara (texto seleccionable).",
        )
    if not parsed.contracts:
        detail = parsed.warnings[0] if parsed.warnings else (
            "Este archivo no parece un certificado RUP. Sube el PDF que expide la cámara de comercio."
        )
        raise HTTPException(status_code=400, detail=detail)

    name = (company_name or "").strip() or "Mi Empresa"
    try:
        source_key = persist_rup_pdf(
            get_document_storage(),
            company_name=name,
            filename=filename,
            content=content,
        )
    except Exception as exc:
        logger.warning("Failed to store RUP PDF for %s: %s", name, exc)
        raise HTTPException(status_code=500, detail="No se pudo guardar el certificado RUP.") from exc

    try:
        imported = replace_experiences_from_rup(db, company_name=name, parsed=parsed)
        capacity = upsert_capacity(
            db,
            company_name=name,
            parsed=parsed,
            source_pdf_key=source_key,
            source_pdf_filename=filename,
        )
        db.commit()
        db.refresh(capacity)
    except ProgrammingError as exc:
        db.rollback()
        logger.exception("RUP schema missing for %s: %s", name, exc)
        raise HTTPException(
            status_code=500,
            detail="El perfil RUP aún no está listo en la base de datos. Espera un minuto e inténtalo de nuevo.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("RUP persist failed for %s: %s", name, exc)
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la experiencia extraída del RUP.",
        ) from exc

    return RupImportResponse(
        imported_experiences=imported,
        capacity=_capacity_payload(capacity),
        issued_at=capacity.issued_at,
        valid_until=capacity.valid_until,
        nit=capacity.nit,
        razon_social=capacity.razon_social,
        warnings=parsed.warnings,
        message=f"Se cargaron {imported} experiencias desde el RUP.",
    )


@router.get("/rup/profile", response_model=RupProfileResponse)
def get_rup_profile(
    company_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    row = (
        db.query(CompanyCapacity)
        .filter(CompanyCapacity.company_name == company_name.strip())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Esta empresa aún no tiene un RUP cargado.")

    experiences_count = (
        db.query(CompanyExperience)
        .filter(CompanyExperience.company_name == company_name.strip())
        .count()
    )
    return RupProfileResponse(
        id=row.id,
        company_name=row.company_name,
        nit=row.nit,
        razon_social=row.razon_social,
        camara=row.camara,
        issued_at=row.issued_at,
        valid_until=row.valid_until,
        capacity=_capacity_payload(row),
        source_pdf_filename=row.source_pdf_filename,
        experiences_count=experiences_count,
        updated_at=row.updated_at,
        warnings=_warnings(row),
    )
