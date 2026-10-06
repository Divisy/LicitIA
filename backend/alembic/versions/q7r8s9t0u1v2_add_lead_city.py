"""add city to leads

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-10-06 15:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "q7r8s9t0u1v2"
down_revision: Union[str, None] = "p6q7r8s9t0u1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS city VARCHAR(120);
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS city;")
