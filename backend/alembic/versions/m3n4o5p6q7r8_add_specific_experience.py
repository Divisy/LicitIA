"""Add specific experience evidence fields to company_experiences.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-10-02 23:55:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, None] = "l2m3n4o5p6q7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_experience TEXT"
    )
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_evidence_filename VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS specific_evidence_key VARCHAR(500)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS specific_evidence_key")
    op.execute(
        "ALTER TABLE company_experiences DROP COLUMN IF EXISTS specific_evidence_filename"
    )
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS specific_experience")
