"""API endpoints for lead capture (email sign-ups)."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.lead import Lead
from datetime import datetime
from typing import Optional

router = APIRouter()


class LeadCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    role: Optional[str] = None
    source: Optional[str] = "landing_page"


class LeadResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    role: Optional[str]
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/leads", response_model=LeadResponse, status_code=201)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """
    Capture a lead (email sign-up) from the landing page.
    Returns existing lead if email already exists.
    """
    try:
        # Check if lead already exists
        existing_lead = db.query(Lead).filter(Lead.email == lead.email).first()
        
        if existing_lead:
            # Update if new info provided
            if lead.name and not existing_lead.name:
                existing_lead.name = lead.name
            if lead.company and not existing_lead.company:
                existing_lead.company = lead.company
            if lead.industry:
                existing_lead.industry = lead.industry
            if lead.company_size:
                existing_lead.company_size = lead.company_size
            if lead.role:
                existing_lead.role = lead.role
            if lead.source:
                existing_lead.source = lead.source
            existing_lead.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_lead)
            return existing_lead
        
        # Create new lead
        new_lead = Lead(
            email=lead.email,
            name=lead.name,
            company=lead.company,
            industry=lead.industry,
            company_size=lead.company_size,
            role=lead.role,
            source=lead.source or "landing_page",
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
        
        return new_lead
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating lead: {str(e)}")


@router.get("/leads", response_model=list[LeadResponse])
async def list_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all leads (admin only - add auth later)."""
    leads = db.query(Lead).offset(skip).limit(limit).all()
    return leads


@router.get("/leads/check")
async def check_lead_exists(email: str, db: Session = Depends(get_db)):
    """
    Check if a lead (email) exists in the system.
    Returns {exists: true/false, lead: LeadResponse} if exists
    """
    try:
        lead = db.query(Lead).filter(Lead.email == email).first()
        if lead:
            return {
                "exists": True,
                "lead": LeadResponse(
                    id=lead.id,
                    email=lead.email,
                    name=lead.name,
                    company=lead.company,
                    industry=lead.industry,
                    company_size=lead.company_size,
                    role=lead.role,
                    source=lead.source,
                    created_at=lead.created_at
                )
            }
        return {"exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking lead: {str(e)}")

