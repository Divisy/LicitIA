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

from app.core.logging import get_logger
from app.models.company_capacity import CompanyCapacity
from app.models.company_experience import CompanyExperience
from app.services.document_storage import DocumentStorageService, get_document_storage
from app.services.experience_matching import extract_keywords
from app.services.rup_contract_kind import unspsc_codes_from_stored
from app.services.rup_parser import RupParseResult, extract_text_from_pdf_bytes, parse_rup_text, resolve_contractor_name

logger = get_logger(__name__)

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


def _smmlv(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")) or number <= 0:
        return None
    return round(number, 4)


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


def ensure_specific_experience_columns(db: Session) -> None:
    db.execute(
        text(
            "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_experience TEXT"
        )
    )
    db.execute(
        text(
            "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS "
            "specific_evidence_filename VARCHAR(255)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS "
            "specific_evidence_key VARCHAR(500)"
        )
    )
    db.execute(
        text(
            "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS "
            "contractor_name VARCHAR(500)"
        )
    )
    db.execute(
        text("ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS unspsc_codes TEXT")
    )
    db.execute(
        text(
            "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS "
            "amount_smmlv NUMERIC(18, 4)"
        )
    )
    db.commit()



def persist_pdf_bytes(
    storage: DocumentStorageService,
    *,
    object_key: str,
    content: bytes,
) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
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


def persist_rup_pdf(
    storage: DocumentStorageService,
    *,
    company_name: str,
    filename: str,
    content: bytes,
) -> str:
    slug = slugify_company(company_name)
    object_key = f"rup/{slug}/rup.pdf"
    return persist_pdf_bytes(storage, object_key=object_key, content=content)


def replace_experiences_from_rup(
    db: Session,
    *,
    company_name: str,
    parsed: RupParseResult,
) -> int:
    existing = (
        db.query(CompanyExperience)
        .filter(CompanyExperience.company_name == company_name)
        .all()
    )
    evidence_by_contract: dict[str, tuple[Optional[str], Optional[str], Optional[str]]] = {}
    for row in existing:
        number = (row.contract_number or "").strip().upper()
        if not number:
            continue
        if getattr(row, "specific_experience", None) or getattr(row, "specific_evidence_key", None):
            evidence_by_contract[number] = (
                getattr(row, "specific_experience", None),
                getattr(row, "specific_evidence_filename", None),
                getattr(row, "specific_evidence_key", None),
            )
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
        previous = evidence_by_contract.get((contract.contract_number or "").strip().upper())
        specific_text = previous[0] if previous else None
        specific_name = previous[1] if previous else None
        specific_key = previous[2] if previous else None
        experience = CompanyExperience(
            id=uuid.uuid4(),
            company_name=_clip(company_name, 255) or "Mi Empresa",
            contract_number=_clip(contract.contract_number, 100),
            project_description=description,
            contractor_name=_clip(
                resolve_contractor_name(
                    stored=contract.contractor,
                    description=description,
                    razon_social=parsed.razon_social,
                ),
                500,
            ),
            contracting_entity=_clip(contract.entity, 500),
            completion_date=contract.completion_date,
            amount=_money(contract.amount_cop),
            amount_smmlv=_smmlv(contract.amount_smmlv),
            category=_clip(contract.category, 200),
            engineering_area=_clip(contract.contract_kind, 200),
            department=_clip(contract.department, 100),
            municipality=_clip(contract.municipality, 100),
            keywords=json.dumps(keywords) if keywords else None,
            unspsc_codes=json.dumps(contract.unspsc_codes, ensure_ascii=False)
            if contract.unspsc_codes
            else None,
            specific_experience=specific_text,
            specific_evidence_filename=_clip(specific_name, 255),
            specific_evidence_key=_clip(specific_key, 500),
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


def backfill_capacity_from_stored_rup(db: Session, row: CompanyCapacity) -> CompanyCapacity:
    """Re-read the saved RUP when financial/organizational indicators were not stored."""
    missing = (
        row.liquidity is None
        and row.indebtedness is None
        and row.interest_coverage is None
        and row.return_on_equity is None
        and row.return_on_assets is None
    )
    if not missing or not row.source_pdf_key:
        return row
    try:
        content = b"".join(get_document_storage().iter_file_chunks(row.source_pdf_key))
        parsed = parse_rup_text(extract_text_from_pdf_bytes(content), use_llm=False)
    except Exception as exc:
        logger.warning("No se pudo reextraer indicadores del RUP de %s: %s", row.company_name, exc)
        return row
    if (
        parsed.liquidity is None
        and parsed.indebtedness is None
        and parsed.return_on_equity is None
        and parsed.return_on_assets is None
    ):
        return row
    upsert_capacity(
        db,
        company_name=row.company_name,
        parsed=parsed,
        source_pdf_key=row.source_pdf_key,
        source_pdf_filename=row.source_pdf_filename or "rup.pdf",
    )
    db.commit()
    db.refresh(row)
    return row


def backfill_rup_fields_from_stored_pdf(
    db: Session,
    experiences: list[CompanyExperience],
) -> None:
    """Re-read the saved RUP PDF when imported rows lack UNSPSC or SMMLV."""

    def needs_unspsc(row: CompanyExperience) -> bool:
        return not unspsc_codes_from_stored(stored_json=getattr(row, "unspsc_codes", None))

    def needs_smmlv(row: CompanyExperience) -> bool:
        if getattr(row, "amount_smmlv", None) is not None:
            return False
        return (row.contract_number or "").upper().startswith("RUP-")

    missing = [row for row in experiences if needs_unspsc(row) or needs_smmlv(row)]
    if not missing:
        return

    names = {row.company_name for row in missing if row.company_name}
    if not names:
        return
    capacities = (
        db.query(CompanyCapacity).filter(CompanyCapacity.company_name.in_(names)).all()
    )
    capacity_by_name = {(row.company_name or "").lower(): row for row in capacities}
    storage = get_document_storage()
    parsed_by_company: dict[str, dict[str, object]] = {}
    for name in names:
        capacity = capacity_by_name.get((name or "").lower())
        if not capacity or not capacity.source_pdf_key:
            continue
        try:
            content = b"".join(storage.iter_file_chunks(capacity.source_pdf_key))
            parsed = parse_rup_text(extract_text_from_pdf_bytes(content), use_llm=False)
        except Exception as exc:
            logger.warning("No se pudo reextraer campos del RUP de %s: %s", name, exc)
            continue
        parsed_by_company[name.lower()] = {
            (contract.contract_number or "").strip().upper(): contract
            for contract in parsed.contracts
            if contract.contract_number
        }

    updated = False
    for row in missing:
        contract = (parsed_by_company.get((row.company_name or "").lower()) or {}).get(
            (row.contract_number or "").strip().upper()
        )
        if not contract:
            continue
        if needs_unspsc(row) and contract.unspsc_codes:
            row.unspsc_codes = json.dumps(contract.unspsc_codes, ensure_ascii=False)
            updated = True
        smmlv = _smmlv(contract.amount_smmlv)
        if needs_smmlv(row) and smmlv is not None:
            row.amount_smmlv = smmlv
            updated = True
    if updated:
        db.commit()
