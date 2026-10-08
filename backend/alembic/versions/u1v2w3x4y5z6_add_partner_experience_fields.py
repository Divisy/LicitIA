"""Store partner experience transferred to the company.

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-10-08 16:55:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, None] = "t0u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    statements = [
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
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_company_experiences_import_key")
    for column in (
        "import_key",
        "notes",
        "sheet_metrics",
        "civil_areas",
        "partner_name",
        "partner_code",
        "suspension_months",
        "duration_months",
        "participation_percent",
        "smmlv_total",
        "contract_amount",
        "start_date",
    ):
        op.execute(f"ALTER TABLE company_experiences DROP COLUMN IF EXISTS {column}")
