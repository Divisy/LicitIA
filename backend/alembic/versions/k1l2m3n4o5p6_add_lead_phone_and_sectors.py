"""add phone and sectors to leads (US 2.0)

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-10-02 16:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "k1l2m3n4o5p6"
down_revision: Union[str, None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
        """
    )
    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS sectors VARCHAR(255);
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS sectors;")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS phone;")
