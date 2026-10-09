"""Tender Pydantic schemas."""
from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class ExperienceFitContract(BaseModel):
    """A company contract that entered the general-experience sum."""
    experience_id: str
    contract_number: Optional[str] = None
    contracting_entity: Optional[str] = None
    amount_smmlv: Optional[float] = None
    in_general_sum: bool = False
    specific_met: bool = False
    matched_activity: Optional[str] = None


class ExperienceFit(BaseModel):
    """Whether the company can bid, from acta partidas and the pliego."""
    status: str
    reason: str
    general_sum_smmlv: Optional[float] = None
    general_minimum_smmlv: Optional[float] = None
    contracts: List[ExperienceFitContract] = Field(default_factory=list)


class TenderResponse(BaseModel):
    """Tender response schema."""
    id: UUID
    external_id: str
    reference: Optional[str] = None
    source: str
    entity_name: str
    object_text: str
    current_phase: Optional[str] = None
    department: Optional[str] = None
    municipality: Optional[str] = None
    location: Optional[str] = None
    amount: Optional[float] = None
    publication_date: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    state: str
    apertura_estado: Optional[str] = None
    process_url: str
    contract_type: Optional[str] = None
    contract_modality: Optional[str] = None
    unspsc_code: Optional[str] = None
    relevance_score: Optional[float] = None
    is_relevant_interventoria_vial: bool
    documents_extraction_attempted_at: Optional[datetime] = None
    experience_match_score: Optional[float] = Field(None, description="Match score against company experiences (0-1)")
    matching_experiences: Optional[List[dict]] = Field(None, description="List of matching experiences")
    experience_fit: Optional[ExperienceFit] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def set_location(self) -> "TenderResponse":
        if not self.location:
            parts = [p for p in (self.department, self.municipality) if p]
            self.location = ", ".join(parts) if parts else None
        return self

    class Config:
        from_attributes = True


class TenderListResponse(BaseModel):
    """Paginated tender list response."""
    items: List[TenderResponse]
    total: int
    limit: int
    offset: int


class TenderDocumentResponse(BaseModel):
    """Downloaded tender document metadata."""
    id: UUID
    tender_id: UUID
    external_document_id: str
    document_type: str
    file_name: str
    file_path: str
    download_url: str
    file_size: Optional[int] = None
    extension: Optional[str] = None
    description: Optional[str] = None
    downloaded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenderDocumentListResponse(BaseModel):
    """List of documents for a tender."""
    items: List[TenderDocumentResponse]
    total: int
