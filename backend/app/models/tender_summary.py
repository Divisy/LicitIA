from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.db import Base


class TenderSummary(Base):
    """Extracted general information for a tender."""

    __tablename__ = "tender_summaries"

    tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contract_kind = Column(String(50), nullable=False, default="desconocido")
    summary_json = Column(JSONB, nullable=False, default=dict)
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tender = relationship("Tender", back_populates="summary")

    def __repr__(self) -> str:
        return f"<TenderSummary(tender_id={self.tender_id}, contract_kind={self.contract_kind})>"
