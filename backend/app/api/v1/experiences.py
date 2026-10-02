"""Company Experience API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import tempfile
import os

from app.core.db import get_db
from app.models.company_capacity import CompanyCapacity
from app.models.company_experience import CompanyExperience
from app.schemas.company_experience import (
    CompanyExperienceCreate,
    CompanyExperienceResponse,
    CompanyExperienceListResponse,
    ExcelImportResponse
)
from app.services.excel_import import import_experiences_from_excel
from app.services.rup_contract_kind import kind_payload_for_experience, unspsc_codes_from_stored
from app.services.rup_import import backfill_rup_fields_from_stored_pdf, ensure_specific_experience_columns
from app.services.rup_parser import resolve_contractor_name
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _razon_social_for(db: Session, company_name: Optional[str]) -> Optional[str]:
    if not company_name:
        return None
    row = (
        db.query(CompanyCapacity)
        .filter(CompanyCapacity.company_name.ilike(company_name.strip()))
        .first()
    )
    return row.razon_social if row and row.razon_social else None


def _experience_dict(
    experience: CompanyExperience,
    keywords,
    *,
    razon_social: Optional[str] = None,
) -> dict:
    kind, label = kind_payload_for_experience(
        engineering_area=experience.engineering_area,
        project_description=experience.project_description,
        category=experience.category,
        contract_number=experience.contract_number,
    )
    return {
        "id": experience.id,
        "company_name": experience.company_name,
        "contract_number": experience.contract_number,
        "project_description": experience.project_description,
        "contracting_entity": experience.contracting_entity,
        "contractor_name": resolve_contractor_name(
            stored=getattr(experience, "contractor_name", None),
            description=experience.project_description,
            razon_social=razon_social,
            account_name=experience.company_name,
        ),
        "completion_date": experience.completion_date,
        "amount": float(experience.amount) if experience.amount else None,
        "amount_smmlv": float(experience.amount_smmlv)
        if getattr(experience, "amount_smmlv", None)
        else None,
        "category": experience.category,
        "engineering_area": experience.engineering_area,
        "contract_kind": kind,
        "contract_kind_label": label,
        "specific_experience": experience.specific_experience,
        "specific_evidence_filename": experience.specific_evidence_filename,
        "unspsc_codes": unspsc_codes_from_stored(
            stored_json=getattr(experience, "unspsc_codes", None),
        ),
        "keywords": keywords,
        "created_at": experience.created_at,
        "updated_at": experience.updated_at,
    }


@router.post("/experiences", response_model=CompanyExperienceResponse, status_code=201)
async def create_experience(
    experience: CompanyExperienceCreate,
    db: Session = Depends(get_db),
):
    """Create a new company experience."""
    from app.services.experience_matching import extract_keywords
    import json
    
    # Extract keywords
    keywords = extract_keywords(experience.project_description)
    keywords_json = json.dumps(keywords) if keywords else None
    
    db_experience = CompanyExperience(
        **experience.model_dump(),
        keywords=keywords_json
    )
    db.add(db_experience)
    db.commit()
    db.refresh(db_experience)
    return CompanyExperienceResponse.model_validate(
        _experience_dict(
            db_experience,
            json.loads(db_experience.keywords) if db_experience.keywords else None,
            razon_social=_razon_social_for(db, db_experience.company_name),
        )
    )


@router.get("/experiences", response_model=CompanyExperienceListResponse)
async def list_experiences(
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    hydrate_rup: bool = Query(
        False,
        description="Re-read the stored RUP PDF to fill UNSPSC/SMMLV on this page only",
    ),
    db: Session = Depends(get_db),
):
    """List company experiences."""
    ensure_specific_experience_columns(db)
    query = db.query(CompanyExperience)
    
    if company_name:
        query = query.filter(CompanyExperience.company_name.ilike(f"%{company_name}%"))
    
    total = query.count()
    # Handle None completion_date for ordering
    from sqlalchemy import case
    experiences = query.order_by(
        case((CompanyExperience.completion_date.is_(None), 1), else_=0),
        CompanyExperience.completion_date.desc()
    ).offset(offset).limit(limit).all()
    if hydrate_rup:
        backfill_rup_fields_from_stored_pdf(db, experiences)

    # Parse keywords for response
    import json
    razon_by: dict[str, str] = {}
    names = {exp.company_name for exp in experiences if exp.company_name}
    if names:
        for row in db.query(CompanyCapacity).filter(CompanyCapacity.company_name.in_(names)).all():
            if row.razon_social:
                razon_by[(row.company_name or "").lower()] = row.razon_social
    items = []
    for exp in experiences:
        exp_dict = _experience_dict(
            exp,
            json.loads(exp.keywords) if exp.keywords else None,
            razon_social=razon_by.get((exp.company_name or "").lower()),
        )
        exp_data = CompanyExperienceResponse.model_validate(exp_dict)
        items.append(exp_data)
    
    return CompanyExperienceListResponse(items=items, total=total)


@router.get("/experiences/{experience_id}", response_model=CompanyExperienceResponse)
async def get_experience(
    experience_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single experience by ID."""
    experience = db.query(CompanyExperience).filter(CompanyExperience.id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    import json
    exp_dict = _experience_dict(
        experience,
        json.loads(experience.keywords) if experience.keywords else None,
        razon_social=_razon_social_for(db, experience.company_name),
    )
    response_data = CompanyExperienceResponse.model_validate(exp_dict)
    return response_data


@router.post(
    "/experiences/{experience_id}/specific-evidence",
    response_model=CompanyExperienceResponse,
)
async def upload_specific_evidence(
    experience_id: UUID,
    file: UploadFile = File(..., description="Certificado o acta de finalización en PDF"),
    db: Session = Depends(get_db),
):
    """Attach the certificate or completion acta that states the specific experience."""
    import json
    from datetime import datetime

    from app.config import settings
    from app.services.document_storage import get_document_storage
    from app.services.experience_matching import extract_keywords
    from app.services.rup_import import (
        ensure_specific_experience_columns,
        persist_pdf_bytes,
        slugify_company,
    )
    from app.services.rup_parser import extract_text_from_pdf_bytes
    from app.services.specific_experience import extract_specific_experience_from_text

    ensure_specific_experience_columns(db)
    experience = db.query(CompanyExperience).filter(CompanyExperience.id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")

    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Sube el certificado o el acta de finalización en PDF.",
        )

    content = await file.read()
    max_bytes = min(getattr(settings, "RUP_UPLOAD_MAX_BYTES", 26_214_400), 26_214_400)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño máximo (25 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    storage = get_document_storage()
    slug = slugify_company(experience.company_name or "empresa")
    object_key = f"rup/{slug}/experiences/{experience.id}/acta.pdf"
    try:
        persist_pdf_bytes(storage, object_key=object_key, content=content)
    except Exception as exc:
        logger.exception("Failed to store specific evidence for %s", experience_id)
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar el certificado o el acta.",
        ) from exc

    extracted = extract_specific_experience_from_text(extract_text_from_pdf_bytes(content))
    experience.specific_evidence_filename = filename[:255]
    experience.specific_evidence_key = object_key[:500]
    if extracted:
        experience.specific_experience = extracted
        keywords = extract_keywords(extracted)
        experience.keywords = json.dumps(keywords) if keywords else experience.keywords
    experience.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(experience)
    return CompanyExperienceResponse.model_validate(
        _experience_dict(
            experience,
            json.loads(experience.keywords) if experience.keywords else None,
            razon_social=_razon_social_for(db, experience.company_name),
        )
    )


@router.post("/experiences/import", response_model=ExcelImportResponse)
async def import_experiences(
    file: UploadFile = File(..., description="Excel file with company experiences"),
    company_name: str = Query("BEC", description="Company name (defaults to BEC)"),
    db: Session = Depends(get_db),
):
    """
    Import company experiences from Excel file.
    
    Expected columns:
    - EMPRESA
    - CONTRATO No.
    - OBRA (required)
    - ENTIDAD CONTRATANTE
    - FECHA FINALIZACIÓN
    - VALOR ACTUAL
    - CATEGORÍA
    - ÁREA DE LA INGENIERÍA CIVIL
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        try:
            # Read file content
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
            
            # Import experiences
            imported, errors = import_experiences_from_excel(tmp_file_path, company_name)
            
            if errors:
                message = f"Imported {imported} experiences with {len(errors)} errors"
            else:
                message = f"Successfully imported {imported} experiences"
            
            return ExcelImportResponse(
                imported=imported,
                errors=errors,
                message=message
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


@router.delete("/experiences/{experience_id}", status_code=204)
async def delete_experience(
    experience_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete an experience."""
    experience = db.query(CompanyExperience).filter(CompanyExperience.id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    db.delete(experience)
    db.commit()
    return None

