"""Tender summary schemas (US 1.4)."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class TenderSummaryFieldResponse(BaseModel):
    key: str
    label: str
    priority: str
    source: str
    status: str
    value: Any = None
    display_value: Optional[str] = None
    source_document_id: Optional[str] = None


class TenderSummaryResponse(BaseModel):
    tender_id: UUID
    contract_kind: str
    contract_kind_label: str
    extracted_at: datetime
    fields: List[TenderSummaryFieldResponse]
    cached: bool = False
