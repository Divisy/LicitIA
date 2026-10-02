"""Store UNSPSC codes extracted from each RUP contract.

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-10-03 00:20:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "o5p6q7r8s9t0"
down_revision: Union[str, None] = "n4o5p6q7r8s9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS unspsc_codes TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS unspsc_codes")
