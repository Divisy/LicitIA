"""Tender document model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.db import Base


class TenderDocument(Base):
    """Downloaded SECOP document linked to a tender."""

    __tablename__ = "tender_documents"
    __table_args__ = (
        UniqueConstraint("tender_id", "external_document_id", name="uq_tender_document"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    external_document_id = Column(String(100), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    download_url = Column(String(2000), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    extension = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tender = relationship("Tender", back_populates="documents")

    def __repr__(self) -> str:
        return f"<TenderDocument(id={self.id}, type={self.document_type}, file={self.file_name})>"
