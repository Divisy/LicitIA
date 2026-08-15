"""Tender model."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, Numeric, DateTime, Float, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base
import enum


class TenderSource(str, enum.Enum):
    """Tender source enumeration."""
    SECOP_I = "SECOP_I"
    SECOP_II = "SECOP_II"
    SECOP_INTEGRADO = "SECOP_INTEGRADO"


class Tender(Base):
    """Tender model representing a public tender from SECOP."""
    
    __tablename__ = "tenders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    reference = Column(String(255), nullable=True, index=True)
    source = Column(SQLEnum(TenderSource), nullable=False)
    entity_name = Column(String(500), nullable=False)
    object_text = Column(Text, nullable=False)
    current_phase = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    municipality = Column(String(100), nullable=True)
    amount = Column(Numeric(18, 2), nullable=True)
    publication_date = Column(DateTime, nullable=True, index=True)
    closing_date = Column(DateTime, nullable=True)
    state = Column(String(100), nullable=False)
    apertura_estado = Column(String(50), nullable=True)  # Estado de apertura: "Abierto" o "Cerrado"
    process_url = Column(String(1000), nullable=False)
    contract_type = Column(String(200), nullable=True)  # Tipo de contrato
    contract_modality = Column(String(200), nullable=True)  # Modalidad de contratación
    unspsc_code = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    relevance_score = Column(Float, nullable=True)
    is_relevant_interventoria_vial = Column(Boolean, default=False, nullable=False, index=True)
    
    @property
    def location(self) -> Optional[str]:
        parts = [p for p in (self.department, self.municipality) if p]
        return ", ".join(parts) if parts else None
    
    def __repr__(self):
        return f"<Tender(id={self.id}, external_id={self.external_id}, entity={self.entity_name})>"

