"""Import the partner experience sheet as BEC company experience.

OHG (Otto Harry) and BEVB (Beatriz) are BEC partners. Their contracts were
transferred to BEC, so every row is stored under company_name BEC and keeps
the partner, participation and SMMLV share for later tender matching.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.company_experience import CompanyExperience
from app.services.experience_matching import extract_keywords
from app.services.project_typology import apply_project_typologies

COMPANY_NAME = "BEC"
PARTNERS = {
    "OHG": "Otto Harry",
    "BEVB": "Beatriz",
}

_SCHEMA_READY = False


@dataclass
class BecExperienceRow:
    sheet_no: str
    partner_code: str
    partner_name: str
    contract_number: Optional[str]
    project_description: str
    contracting_entity: Optional[str]
    contractor_name: Optional[str]
    start_date: Optional[date]
    completion_date: Optional[date]
    suspension_months: Optional[Decimal]
    duration_months: Optional[Decimal]
    contract_amount: Optional[Decimal]
    smmlv_unit: Optional[Decimal]
    smmlv_total: Optional[Decimal]
    participation_percent: Optional[Decimal]
    amount_smmlv: Optional[Decimal]
    pfm_total: Optional[Decimal]
    pfm_share: Optional[Decimal]
    amount: Optional[Decimal]
    category: Optional[str]
    civil_areas: list[str]
    specific_experience: Optional[str]
    notes: Optional[str]
    rup_item: Optional[str]
    import_key: str


def parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    """Parse a Colombian spreadsheet number: 1.219,50 or $415.680.829,5."""
    if value is None:
        return None
    text_value = str(value).strip().replace("\xa0", "").replace(" ", "")
    if not text_value:
        return None
    text_value = text_value.replace("$", "").replace("%", "")
    if not text_value or set(text_value) <= {"-", ".", ","}:
        return None
    if "," in text_value:
        text_value = text_value.replace(".", "").replace(",", ".")
    elif text_value.count(".") > 1:
        text_value = text_value.replace(".", "")
    try:
        return Decimal(text_value)
    except InvalidOperation:
        return None


def parse_sheet_date(value: Optional[str]) -> Optional[date]:
    text_value = " ".join(str(value or "").split())
    if not text_value:
        return None
    return datetime.strptime(text_value, "%d/%m/%Y").date()


def _clean(value: Optional[str]) -> Optional[str]:
    text_value = " ".join(str(value or "").replace("\n", " ").split())
    if not text_value or text_value.lower() in {"nan", "none", "-"}:
        return None
    return text_value


def _decimal_json(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    return format(value, "f")


def _clip(value: Optional[str], limit: int) -> Optional[str]:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return cleaned[:limit]


def _header_map(fieldnames: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for name in fieldnames:
        key = " ".join((name or "").replace("\ufeff", "").split()).upper()
        if key:
            mapped[key] = name
    return mapped


def _cell(row: dict, headers: dict[str, str], *candidates: str) -> str:
    for candidate in candidates:
        source = headers.get(candidate)
        if source is None:
            continue
        return row.get(source) or ""
    return ""


def _import_key(
    *,
    partner_code: str,
    sheet_no: str,
    contract_number: Optional[str],
    start_date: Optional[date],
    participation_percent: Optional[Decimal],
    project_description: str,
) -> str:
    material = "|".join(
        [
            partner_code,
            sheet_no,
            contract_number or "",
            start_date.isoformat() if start_date else "",
            format(participation_percent, "f") if participation_percent is not None else "",
            " ".join(project_description.split())[:180],
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _contractor_name(
    proponente: Optional[str],
    *,
    partner_code: str,
    partner_name: str,
) -> str:
    cleaned = _clean(proponente)
    if not cleaned or cleaned.upper() == partner_code:
        return partner_name
    return cleaned


def parse_bec_experience_csv(file_path: str | Path) -> tuple[list[BecExperienceRow], list[str]]:
    """Read the semicolon CSV. Skips the totals row and blank lines."""
    path = Path(file_path)
    raw = path.read_bytes()
    try:
        text_value = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_value = raw.decode("latin-1")
    if text_value.startswith(";"):
        text_value = text_value.split("\n", 1)[1]

    reader = csv.DictReader(io.StringIO(text_value), delimiter=";")
    if not reader.fieldnames:
        return [], ["El archivo no tiene encabezados."]
    headers = _header_map(reader.fieldnames)
    rows: list[BecExperienceRow] = []
    errors: list[str] = []

    for index, source in enumerate(reader, start=2):
        empresa = (_cell(source, headers, "EMPRESA") or "").strip().upper()
        obra = _clean(_cell(source, headers, "OBRA"))
        if not empresa and not obra:
            continue
        if empresa not in PARTNERS:
            errors.append(f"Fila {index}: empresa '{empresa or 'vacía'}' no es OHG ni BEVB.")
            continue
        if not obra:
            errors.append(f"Fila {index}: contrato de {empresa} sin obra.")
            continue

        partner_name = PARTNERS[empresa]
        contract_number = _clip(_cell(source, headers, "CONTRATO NO.", "CONTRATO NO"), 100)
        sheet_no = _clean(_cell(source, headers, "NO.")) or str(index)
        try:
            start_date = parse_sheet_date(_cell(source, headers, "FECHA INICIO"))
            completion_date = parse_sheet_date(_cell(source, headers, "FECHA FINALIZACIÓN", "FECHA FINALIZACION"))
        except ValueError as exc:
            errors.append(f"Fila {index}: fecha inválida ({exc}).")
            start_date = None
            completion_date = None

        areas = [
            area
            for area in (
                _clean(_cell(source, headers, "ÁREA DE LA INGENIERÍA CIVIL", "AREA DE LA INGENIERIA CIVIL")),
                _clean(_cell(source, headers, "ÁREA DE LA INGENIERÍA CIVIL 2", "AREA DE LA INGENIERIA CIVIL 2")),
                _clean(_cell(source, headers, "ÁREA DE LA INGENIERÍA CIVIL 3", "AREA DE LA INGENIERIA CIVIL 3")),
            )
            if area
        ]
        specific_parts = [
            part
            for number in range(1, 6)
            if (
                part := _clean(
                    _cell(
                        source,
                        headers,
                        f"EXPERIENCIA ESPECÍFICA {number}",
                        f"EXPERIENCIA ESPECIFICA {number}",
                    )
                )
            )
        ]
        notes = _clean(_cell(source, headers, "OBSERVACIONES"))
        specific_experience = " · ".join(specific_parts) or None
        if notes:
            specific_experience = (
                f"{specific_experience}\n{notes}" if specific_experience else notes
            )

        participation = parse_decimal(_cell(source, headers, "% PARTICIPACIÓN", "% PARTICIPACION"))
        row = BecExperienceRow(
            sheet_no=sheet_no,
            partner_code=empresa,
            partner_name=partner_name,
            contract_number=contract_number,
            project_description=obra,
            contracting_entity=_clip(_cell(source, headers, "ENTIDAD CONTRATANTE"), 500),
            contractor_name=_clip(
                _contractor_name(
                    _cell(source, headers, "PROPONENTE"),
                    partner_code=empresa,
                    partner_name=partner_name,
                ),
                500,
            ),
            start_date=start_date,
            completion_date=completion_date,
            suspension_months=parse_decimal(_cell(source, headers, "SUSPENSIÓN (MES)", "SUSPENSION (MES)")),
            duration_months=parse_decimal(_cell(source, headers, "DURAC. EN MESES")),
            contract_amount=parse_decimal(_cell(source, headers, "VALOR EN PESOS")),
            smmlv_unit=parse_decimal(_cell(source, headers, "VALOR SMMLV")),
            smmlv_total=parse_decimal(_cell(source, headers, "SMMLV TOTAL")),
            participation_percent=participation,
            amount_smmlv=parse_decimal(_cell(source, headers, "SMLV PARTICIPACIÓN", "SMLV PARTICIPACION")),
            pfm_total=parse_decimal(_cell(source, headers, "PFM TOTAL")),
            pfm_share=parse_decimal(_cell(source, headers, "% PFM")),
            amount=parse_decimal(_cell(source, headers, "VALOR ACTUAL")),
            category=_clip(_cell(source, headers, "CATEGORÍA", "CATEGORIA"), 200),
            civil_areas=areas,
            specific_experience=specific_experience,
            notes=notes,
            rup_item=_clean(_cell(source, headers, "RUP")),
            import_key=_import_key(
                partner_code=empresa,
                sheet_no=sheet_no,
                contract_number=contract_number,
                start_date=start_date,
                participation_percent=participation,
                project_description=obra,
            ),
        )
        rows.append(row)
    return rows, errors


def ensure_partner_experience_columns(db: Session) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    statements = [
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS contractor_name VARCHAR(500)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS amount_smmlv NUMERIC(18, 4)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS unspsc_codes TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_experience TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS project_typologies TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_evidence_filename VARCHAR(255)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_evidence_key VARCHAR(500)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS department VARCHAR(100)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS municipality VARCHAR(100)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS start_date DATE",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS contract_amount NUMERIC(18, 2)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS smmlv_total NUMERIC(18, 4)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS participation_percent NUMERIC(8, 2)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS duration_months NUMERIC(8, 2)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS suspension_months NUMERIC(8, 2)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS partner_code VARCHAR(20)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS partner_name VARCHAR(255)",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS civil_areas TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS sheet_metrics TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS notes TEXT",
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS import_key VARCHAR(64)",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_company_experiences_import_key
        ON company_experiences (import_key)
        WHERE import_key IS NOT NULL
        """,
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()
    _SCHEMA_READY = True


def bec_account_email(db: Session) -> Optional[str]:
    """Email of the BEC account, so the RUP tab lists this experience."""
    try:
        email = db.execute(
            text(
                """
                SELECT lower(btrim(email))
                FROM leads
                WHERE lower(btrim(company)) = 'bec'
                  AND email IS NOT NULL
                  AND btrim(email) <> ''
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        ).scalar()
    except Exception:
        db.rollback()
        return None
    return email or None


def import_bec_experience_rows(
    db: Session,
    rows: list[BecExperienceRow],
) -> tuple[int, int]:
    """Insert or update BEC experiences. Returns (created, updated)."""
    ensure_partner_experience_columns(db)
    owner_email = bec_account_email(db)
    created = 0
    updated = 0
    now = datetime.utcnow()
    for row in rows:
        keyword_text = " ".join(
            part
            for part in (
                row.project_description,
                row.category,
                " ".join(row.civil_areas),
                row.specific_experience,
            )
            if part
        )
        keywords = extract_keywords(keyword_text)
        values = {
            "company_name": COMPANY_NAME,
            "owner_email": owner_email,
            "contract_number": row.contract_number,
            "project_description": row.project_description,
            "contractor_name": row.contractor_name,
            "contracting_entity": row.contracting_entity,
            "start_date": row.start_date,
            "completion_date": row.completion_date,
            "amount": row.amount,
            "amount_smmlv": row.amount_smmlv,
            "contract_amount": row.contract_amount,
            "smmlv_total": row.smmlv_total,
            "participation_percent": row.participation_percent,
            "duration_months": row.duration_months,
            "suspension_months": row.suspension_months,
            "partner_code": row.partner_code,
            "partner_name": row.partner_name,
            "category": row.category,
            "engineering_area": _clip(" · ".join(row.civil_areas), 200),
            "civil_areas": json.dumps(row.civil_areas, ensure_ascii=False) if row.civil_areas else None,
            "sheet_metrics": json.dumps(
                {
                    "sheet_no": row.sheet_no,
                    "rup_item": row.rup_item,
                    "smmlv_unit": _decimal_json(row.smmlv_unit),
                    "pfm_total": _decimal_json(row.pfm_total),
                    "pfm_share": _decimal_json(row.pfm_share),
                },
                ensure_ascii=False,
            ),
            "notes": row.notes,
            "specific_experience": row.specific_experience,
            "keywords": json.dumps(keywords, ensure_ascii=False) if keywords else None,
            "import_key": row.import_key,
            "updated_at": now,
        }
        existing = (
            db.query(CompanyExperience)
            .filter(CompanyExperience.import_key == row.import_key)
            .one_or_none()
        )
        if existing is None:
            experience = CompanyExperience(**values, created_at=now)
            apply_project_typologies(experience)
            db.add(experience)
            created += 1
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            apply_project_typologies(existing)
            updated += 1
    db.commit()
    return created, updated
