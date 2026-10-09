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
    owner_email = Column(String(255), nullable=True, index=True)
    contract_number = Column(String(100), nullable=True)
    project_description = Column(Text, nullable=False)  # OBRA
    contractor_name = Column(String(500), nullable=True)
    contracting_entity = Column(String(500), nullable=True)  # ENTIDAD CONTRATANTE
    completion_date = Column(Date, nullable=True)  # FECHA FINALIZACIÓN
    start_date = Column(Date, nullable=True)  # FECHA INICIO
    amount = Column(Numeric(18, 2), nullable=True)  # pesos if the RUP reported COP
    amount_smmlv = Column(Numeric(18, 4), nullable=True)  # SMMLV printed on the RUP
    contract_amount = Column(Numeric(18, 2), nullable=True)  # valor del contrato en pesos
    smmlv_total = Column(Numeric(18, 4), nullable=True)  # SMMLV del contrato completo
    participation_percent = Column(Numeric(8, 2), nullable=True)
    duration_months = Column(Numeric(8, 2), nullable=True)
    suspension_months = Column(Numeric(8, 2), nullable=True)
    partner_code = Column(String(20), nullable=True)  # OHG, BEVB
    partner_name = Column(String(255), nullable=True)  # socio que trasladó la experiencia
    contract_kind = Column(String(40), nullable=True)  # elección del usuario
    category = Column(String(200), nullable=True)  # CATEGORÍA
    engineering_area = Column(String(200), nullable=True)  # ÁREA DE LA INGENIERÍA CIVIL
    civil_areas = Column(Text, nullable=True)  # JSON array of civil engineering areas
    sheet_metrics = Column(Text, nullable=True)  # JSON: SMMLV del año, PFM, fila de origen
    notes = Column(Text, nullable=True)
    import_key = Column(String(64), nullable=True, unique=True, index=True)
    
    # Geographic location (for improved matching)
    department = Column(String(100), nullable=True)  # Departamento
    municipality = Column(String(100), nullable=True)  # Municipio
    
    # Extracted keywords for matching (computed from project_description)
    keywords = Column(Text, nullable=True)  # JSON array of extracted keywords
    unspsc_codes = Column(Text, nullable=True)  # JSON array of UNSPSC from the RUP

    # Experiencia específica: no viene en el RUP; se carga con certificado o acta.
    specific_experience = Column(Text, nullable=True)
    acta_partidas = Column(Text, nullable=True)  # ítems y cantidades ejecutadas del acta
    project_typologies = Column(Text, nullable=True)  # JSON array from the contract object
    specific_evidence_filename = Column(String(255), nullable=True)
    specific_evidence_key = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<CompanyExperience(id={self.id}, company={self.company_name}, project={self.project_description[:50]}...)>"

