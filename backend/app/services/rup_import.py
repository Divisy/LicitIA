"""Persist a RUP PDF as company experiences + capacity."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.company_capacity import CompanyCapacity
from app.models.company_experience import CompanyExperience
from app.services.document_storage import DocumentStorageService
from app.services.experience_matching import extract_keywords
from app.services.rup_parser import RupParseResult

_CREATE_CAPACITY_SQL = """
CREATE TABLE IF NOT EXISTS company_capacity (
    id UUID PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL UNIQUE,
    nit VARCHAR(32),
    razon_social VARCHAR(500),
    camara VARCHAR(255),
    issued_at DATE,
    valid_until DATE,
    cut_year INTEGER,
    liquidity NUMERIC(18, 6),
    indebtedness NUMERIC(18, 6),
    interest_coverage NUMERIC(18, 6),
    return_on_equity NUMERIC(18, 6),
    return_on_assets NUMERIC(18, 6),
    working_capital NUMERIC(18, 2),
    organizational_json TEXT,
    source_pdf_key VARCHAR(500),
    source_pdf_filename VARCHAR(255),
    extracted_text_chars INTEGER,
    warnings_json TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
)
"""


def slugify_company(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return (slug or "empresa")[:80]


def _clip(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    return text_value[:limit]


def _money(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return round(number, 2)


def ensure_company_capacity_table(db: Session) -> None:
    db.execute(text(_CREATE_CAPACITY_SQL))
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_company_capacity_company_name
            ON company_capacity (company_name)
            """
        )
    )
    db.commit()



def persist_rup_pdf(
    storage: DocumentStorageService,
    *,
    company_name: str,
    filename: str,
    content: bytes,
) -> str:
    slug = slugify_company(company_name)
    object_key = f"rup/{slug}/rup.pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        return storage.persist_local_file(tmp_path, object_key)
    except Exception as exc:
        dest = storage.local_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_path, dest)
        try:
            storage.upload_local_copy(object_key)
        except Exception:
            pass
        if not dest.is_file():
            raise exc
        return object_key
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def replace_experiences_from_rup(
    db: Session,
    *,
    company_name: str,
    parsed: RupParseResult,
) -> int:
    db.query(CompanyExperience).filter(CompanyExperience.company_name == company_name).delete(
        synchronize_session=False
    )
    imported = 0
    now = datetime.utcnow()
    for contract in parsed.contracts:
        description = (contract.object or "").strip()
        if not description:
            continue
        keywords = extract_keywords(description)
        experience = CompanyExperience(
            id=uuid.uuid4(),
            company_name=_clip(company_name, 255) or "Mi Empresa",
            contract_number=_clip(contract.contract_number, 100),
            project_description=description,
            contracting_entity=_clip(contract.entity, 500),
            completion_date=contract.completion_date,
            amount=_money(contract.amount_cop),
            category=_clip(contract.category, 200),
            department=_clip(contract.department, 100),
            municipality=_clip(contract.municipality, 100),
            keywords=json.dumps(keywords) if keywords else None,
            created_at=now,
            updated_at=now,
        )
        db.add(experience)
        imported += 1
    return imported


def upsert_capacity(
    db: Session,
    *,
    company_name: str,
    parsed: RupParseResult,
    source_pdf_key: str,
    source_pdf_filename: str,
) -> CompanyCapacity:
    row = db.query(CompanyCapacity).filter(CompanyCapacity.company_name == company_name).first()
    now = datetime.utcnow()
    if row is None:
        row = CompanyCapacity(id=uuid.uuid4(), company_name=company_name, created_at=now)
        db.add(row)

    row.nit = _clip(parsed.nit, 32)
    row.razon_social = _clip(parsed.razon_social, 500)
    row.camara = _clip(parsed.camara, 255)
    row.issued_at = parsed.issued_at
    row.valid_until = parsed.valid_until
    row.cut_year = parsed.cut_year
    row.liquidity = parsed.liquidity
    row.indebtedness = parsed.indebtedness
    row.interest_coverage = parsed.interest_coverage
    row.return_on_equity = parsed.return_on_equity
    row.return_on_assets = parsed.return_on_assets
    row.working_capital = _money(parsed.working_capital)
    row.organizational_json = json.dumps(parsed.organizational or {}, ensure_ascii=False)
    row.source_pdf_key = _clip(source_pdf_key, 500)
    row.source_pdf_filename = _clip(source_pdf_filename, 255)
    row.extracted_text_chars = parsed.extracted_text_chars
    row.warnings_json = json.dumps(parsed.warnings or [], ensure_ascii=False)
    row.updated_at = now
    return row
