from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class TenderRequirements(Base):
    """Extracted participation requirements for a tender (US 1.5)."""

    __tablename__ = "tender_requirements"

    tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    extraction_version = Column(String(20), nullable=False, default="1.5.1")
    requirements_json = Column(JSONB, nullable=False, default=dict)
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tender = relationship("Tender", back_populates="requirements")

    def __repr__(self) -> str:
        return f"<TenderRequirements(tender_id={self.tender_id})>"
