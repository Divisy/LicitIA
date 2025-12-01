"""Lead model for email capture."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from app.core.db import Base


class Lead(Base):
    """Lead model for capturing email sign-ups from landing page."""
    
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    role = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True, default="landing_page")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

