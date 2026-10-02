"""Schemas for RUP import and company capacity profile."""
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RupCapacityPayload(BaseModel):
    liquidez: Optional[float] = None
    endeudamiento: Optional[float] = None
    cobertura_intereses: Optional[float] = None
    rentabilidad_patrimonio: Optional[float] = None
    rentabilidad_activo: Optional[float] = None
    capital_trabajo: Optional[float] = None
    cut_year: Optional[int] = None
    organizacional: Optional[dict[str, Any]] = None


class RupImportResponse(BaseModel):
    imported_experiences: int
    capacity: RupCapacityPayload
    issued_at: Optional[date] = None
    valid_until: Optional[date] = None
    nit: Optional[str] = None
    razon_social: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    message: str


class RupProfileResponse(BaseModel):
    company_name: str
    nit: Optional[str] = None
    razon_social: Optional[str] = None
    camara: Optional[str] = None
    issued_at: Optional[date] = None
    valid_until: Optional[date] = None
    capacity: RupCapacityPayload
    source_pdf_filename: Optional[str] = None
    experiences_count: int = 0
    updated_at: Optional[datetime] = None
    warnings: list[str] = Field(default_factory=list)
    id: Optional[UUID] = None
