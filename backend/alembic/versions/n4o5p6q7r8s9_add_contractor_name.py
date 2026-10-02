"""Add contractor_name to company_experiences.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-10-03 00:10:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "n4o5p6q7r8s9"
down_revision: Union[str, None] = "m3n4o5p6q7r8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS contractor_name VARCHAR(500)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS contractor_name")
