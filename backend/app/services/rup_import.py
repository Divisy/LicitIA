"""Persist a RUP PDF as company experiences + capacity."""
from __future__ import annotations

import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.company_capacity import CompanyCapacity
from app.models.company_experience import CompanyExperience
from app.services.document_storage import DocumentStorageService
from app.services.experience_matching import extract_keywords
from app.services.rup_parser import RupParseResult


def slugify_company(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return (slug or "empresa")[:80]


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
            company_name=company_name,
            contract_number=contract.contract_number,
            project_description=description,
            contracting_entity=contract.entity,
            completion_date=contract.completion_date,
            amount=contract.amount_cop,
            category=contract.category,
            department=contract.department,
            municipality=contract.municipality,
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

    row.nit = parsed.nit
    row.razon_social = parsed.razon_social
    row.camara = parsed.camara
    row.issued_at = parsed.issued_at
    row.valid_until = parsed.valid_until
    row.cut_year = parsed.cut_year
    row.liquidity = parsed.liquidity
    row.indebtedness = parsed.indebtedness
    row.interest_coverage = parsed.interest_coverage
    row.return_on_equity = parsed.return_on_equity
    row.return_on_assets = parsed.return_on_assets
    row.working_capital = parsed.working_capital
    row.organizational_json = json.dumps(parsed.organizational or {}, ensure_ascii=False)
    row.source_pdf_key = source_pdf_key
    row.source_pdf_filename = source_pdf_filename
    row.extracted_text_chars = parsed.extracted_text_chars
    row.warnings_json = json.dumps(parsed.warnings or [], ensure_ascii=False)
    row.updated_at = now
    return row
