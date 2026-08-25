"""Tender requirements schemas (US 1.5)."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class TenderRequirementItemResponse(BaseModel):
    key: str
    label: str
    value: Any = None
    display_value: Optional[str] = None
    confidence: float = 0.0
    source_document: str
    source_document_id: Optional[str] = None
    evidence: Optional[str] = None


class TenderRequirementSectionResponse(BaseModel):
    key: str
    title: str
    status: str
    items: List[TenderRequirementItemResponse]


class TenderRequirementsResponse(BaseModel):
    tender_id: UUID
    tender_external_id: str
    extraction_version: str
    extracted_at: datetime
    sections: List[TenderRequirementSectionResponse]
    warnings: List[str] = []
    cached: bool = False
