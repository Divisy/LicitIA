"""Company RUP capacity (financial / organizational) for a contractor."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Numeric, DateTime, Date, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class CompanyCapacity(Base):
    """One current RUP capacity row per owner email."""

    __tablename__ = "company_capacity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False, index=True)
    owner_email = Column(String(255), nullable=True, index=True)
    nit = Column(String(32), nullable=True)
    razon_social = Column(String(500), nullable=True)
    camara = Column(String(255), nullable=True)
    issued_at = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    cut_year = Column(Integer, nullable=True)
    liquidity = Column(Numeric(18, 6), nullable=True)
    indebtedness = Column(Numeric(18, 6), nullable=True)
    interest_coverage = Column(Numeric(18, 6), nullable=True)
    return_on_equity = Column(Numeric(18, 6), nullable=True)
    return_on_assets = Column(Numeric(18, 6), nullable=True)
    working_capital = Column(Numeric(18, 2), nullable=True)
    organizational_json = Column(Text, nullable=True)
    source_pdf_key = Column(String(500), nullable=True)
    source_pdf_filename = Column(String(255), nullable=True)
    extracted_text_chars = Column(Integer, nullable=True)
    warnings_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
