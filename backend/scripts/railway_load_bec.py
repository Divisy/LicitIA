"""Load BEC experience JSON from stdin into the database of this process."""
from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text

ALTERS = [
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
    """,
]

INSERT = text(
    """
    INSERT INTO company_experiences (
        id, company_name, owner_email, contract_number, project_description,
        contractor_name, contracting_entity, completion_date, start_date,
        amount, amount_smmlv, contract_amount, smmlv_total, participation_percent,
        duration_months, suspension_months, partner_code, partner_name, category,
        engineering_area, civil_areas, sheet_metrics, notes, specific_experience,
        keywords, project_typologies, import_key, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), :company_name, :owner_email, :contract_number, :project_description,
        :contractor_name, :contracting_entity, :completion_date, :start_date,
        :amount, :amount_smmlv, :contract_amount, :smmlv_total, :participation_percent,
        :duration_months, :suspension_months, :partner_code, :partner_name, :category,
        :engineering_area, :civil_areas, :sheet_metrics, :notes, :specific_experience,
        :keywords, :project_typologies, :import_key, now(), now()
    )
    ON CONFLICT (import_key) DO UPDATE SET
        company_name = EXCLUDED.company_name,
        owner_email = EXCLUDED.owner_email,
        contract_number = EXCLUDED.contract_number,
        project_description = EXCLUDED.project_description,
        contractor_name = EXCLUDED.contractor_name,
        contracting_entity = EXCLUDED.contracting_entity,
        completion_date = EXCLUDED.completion_date,
        start_date = EXCLUDED.start_date,
        amount = EXCLUDED.amount,
        amount_smmlv = EXCLUDED.amount_smmlv,
        contract_amount = EXCLUDED.contract_amount,
        smmlv_total = EXCLUDED.smmlv_total,
        participation_percent = EXCLUDED.participation_percent,
        duration_months = EXCLUDED.duration_months,
        suspension_months = EXCLUDED.suspension_months,
        partner_code = EXCLUDED.partner_code,
        partner_name = EXCLUDED.partner_name,
        category = EXCLUDED.category,
        engineering_area = EXCLUDED.engineering_area,
        civil_areas = EXCLUDED.civil_areas,
        sheet_metrics = EXCLUDED.sheet_metrics,
        notes = EXCLUDED.notes,
        specific_experience = EXCLUDED.specific_experience,
        keywords = EXCLUDED.keywords,
        project_typologies = EXCLUDED.project_typologies,
        updated_at = now()
    """
)


def main() -> None:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgres://"):
        url = "postgresql" + url[len("postgres") :]
    rows = json.load(sys.stdin)
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        for statement in ALTERS:
            conn.execute(text(statement))
        for row in rows:
            conn.execute(INSERT, row)
        total = conn.execute(
            text(
                """
                SELECT count(*)
                FROM company_experiences
                WHERE owner_email = 'direccion@exury.io'
                  AND company_name = 'BEC'
                """
            )
        ).scalar()
    print(f"loaded {len(rows)} visible {total}")


if __name__ == "__main__":
    main()
