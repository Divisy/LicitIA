"""Company Experience model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from app.core.db import Base


class CompanyExperience(Base):
    """Company Experience model representing past projects/contracts."""
    
    __tablename__ = "company_experiences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False, index=True)
    contract_number = Column(String(100), nullable=True)
    project_description = Column(Text, nullable=False)  # OBRA
    contracting_entity = Column(String(500), nullable=True)  # ENTIDAD CONTRATANTE
    completion_date = Column(Date, nullable=True)  # FECHA FINALIZACIÓN
    amount = Column(Numeric(18, 2), nullable=True)  # VALOR ACTUAL
    category = Column(String(200), nullable=True)  # CATEGORÍA
    engineering_area = Column(String(200), nullable=True)  # ÁREA DE LA INGENIERÍA CIVIL
    
    # Geographic location (for improved matching)
    department = Column(String(100), nullable=True)  # Departamento
    municipality = Column(String(100), nullable=True)  # Municipio
    
    # Extracted keywords for matching (computed from project_description)
    keywords = Column(Text, nullable=True)  # JSON array of extracted keywords
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CompanyExperience(id={self.id}, company={self.company_name}, project={self.project_description[:50]}...)>"

