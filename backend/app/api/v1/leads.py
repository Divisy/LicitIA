"""API endpoints for lead capture (email sign-ups)."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.db import get_db
from app.models.lead import Lead
from app.services.login_code import ensure_auth_tables, find_lead_by_email, normalize_email
from app.services.company_email import COMPANY_EMAIL_REQUIRED_MESSAGE, is_company_email
from datetime import datetime
from typing import Optional

router = APIRouter()

ALLOWED_SECTORS = frozenset({"estudios_disenos", "interventoria", "ejecucion_obra"})


def serialize_sectors(sectors: Optional[list[str]]) -> Optional[str]:
    if not sectors:
        return None
    unique = []
    for sector in sectors:
        if sector in ALLOWED_SECTORS and sector not in unique:
            unique.append(sector)
    return ",".join(unique) if unique else None


def parse_sectors(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    return [part for part in raw.split(",") if part in ALLOWED_SECTORS] or None


def ensure_lead_city_column(db: Session) -> None:
    db.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS city VARCHAR(120)"))
    db.commit()


class LeadCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    sectors: Optional[list[str]] = None
    source: Optional[str] = "landing_page"

    @field_validator("sectors")
    @classmethod
    def validate_sectors(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        invalid = [item for item in value if item not in ALLOWED_SECTORS]
        if invalid:
            raise ValueError(f"Invalid sectors: {invalid}")
        return value


class LeadResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    role: Optional[str]
    phone: Optional[str] = None
    city: Optional[str] = None
    sectors: Optional[list[str]] = None
    source: Optional[str]
    created_at: datetime
    onboarding_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def to_lead_response(lead: Lead) -> LeadResponse:
    return LeadResponse(
        id=lead.id,
        email=lead.email,
        name=lead.name,
        company=lead.company,
        industry=lead.industry,
        company_size=lead.company_size,
        role=lead.role,
        phone=lead.phone,
        city=getattr(lead, "city", None),
        sectors=parse_sectors(lead.sectors),
        source=lead.source,
        created_at=lead.created_at,
        onboarding_completed_at=getattr(lead, "onboarding_completed_at", None),
    )


def _apply_lead_fields(target: Lead, payload: LeadCreate) -> None:
    if payload.name:
        target.name = payload.name
    if payload.company:
        target.company = payload.company
    if payload.industry:
        target.industry = payload.industry
    if payload.company_size:
        target.company_size = payload.company_size
    if payload.role:
        target.role = payload.role
    if payload.phone:
        target.phone = payload.phone
    if payload.city:
        target.city = payload.city.strip()[:120]
    serialized = serialize_sectors(payload.sectors)
    if serialized:
        target.sectors = serialized
    if payload.source:
        target.source = payload.source
    target.updated_at = datetime.utcnow()


@router.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Capture a lead (email sign-up) from the landing page.
    Returns existing lead if email already exists.
    """
    try:
        ensure_lead_city_column(db)
        ensure_auth_tables(db)
        email = normalize_email(lead.email)
        existing_lead = find_lead_by_email(db, email)

        if existing_lead:
            _apply_lead_fields(existing_lead, lead)
            db.commit()
            db.refresh(existing_lead)
            return to_lead_response(existing_lead)

        if not is_company_email(email):
            raise HTTPException(status_code=400, detail=COMPANY_EMAIL_REQUIRED_MESSAGE)

        new_lead = Lead(
            email=email,
            name=lead.name,
            company=lead.company,
            industry=lead.industry,
            company_size=lead.company_size,
            role=lead.role,
            phone=lead.phone,
            city=(lead.city.strip()[:120] if lead.city else None),
            sectors=serialize_sectors(lead.sectors),
            source=lead.source or "landing_page",
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
        return to_lead_response(new_lead)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating lead: {str(e)}")


@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all leads (admin only - add auth later)."""
    return [to_lead_response(lead) for lead in db.query(Lead).offset(skip).limit(limit).all()]


@router.get("/leads/check")
async def check_lead_exists(email: str, db: Session = Depends(get_db)):
    """
    Check if a lead (email) exists in the system.
    Returns {exists: true/false, lead: LeadResponse} if exists
    """
    try:
        ensure_lead_city_column(db)
        ensure_auth_tables(db)
        lead = find_lead_by_email(db, email)
        if lead:
            return {"exists": True, "lead": to_lead_response(lead)}
        return {"exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking lead: {str(e)}")


class OnboardingCompletePayload(BaseModel):
    email: EmailStr


@router.post("/leads/onboarding-complete", response_model=LeadResponse)
async def complete_onboarding(
    payload: OnboardingCompletePayload,
    db: Session = Depends(get_db),
):
    ensure_lead_city_column(db)
    ensure_auth_tables(db)
    lead = find_lead_by_email(db, payload.email)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.onboarding_completed_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return to_lead_response(lead)
