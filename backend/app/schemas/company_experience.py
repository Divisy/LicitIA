"""Company Experience Pydantic schemas."""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID


class CompanyExperienceBase(BaseModel):
    """Base experience schema."""
    company_name: str = Field(..., description="Company name")
    contract_number: Optional[str] = None
    project_description: str = Field(..., description="Project/work description (OBRA)")
    contracting_entity: Optional[str] = None
    contractor_name: Optional[str] = None
    completion_date: Optional[date] = None
    amount: Optional[float] = None
    amount_smmlv: Optional[float] = None
    category: Optional[str] = None
    engineering_area: Optional[str] = None
    contract_kind: Optional[str] = None
    contract_kind_label: Optional[str] = None
    specific_experience: Optional[str] = None
    specific_evidence_filename: Optional[str] = None
    project_typologies: List[str] = Field(default_factory=list)


class CompanyExperienceCreate(CompanyExperienceBase):
    """Schema for creating an experience."""
    pass


class CompanyExperienceResponse(CompanyExperienceBase):
    """Schema for experience response."""
    id: UUID
    keywords: Optional[List[str]] = None
    unspsc_codes: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanyExperienceListResponse(BaseModel):
    """Paginated experience list response."""
    items: List[CompanyExperienceResponse]
    total: int
    available_typologies: List[str] = Field(default_factory=list)


class ExcelImportResponse(BaseModel):
    """Response for Excel import."""
    imported: int
    errors: List[str] = []
    message: str

