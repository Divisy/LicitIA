"""add mvp secop fields to tenders

Revision ID: d4f8a1b2c3e4
Revises: 924de1696ecd
Create Date: 2026-08-15 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4f8a1b2c3e4"
down_revision: Union[str, None] = "b42030ef19cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: columns may already exist from init_railway.sh on production.
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS reference VARCHAR(255);
        """
    )
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS current_phase VARCHAR(200);
        """
    )
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS unspsc_code VARCHAR(50);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tenders_reference ON tenders (reference);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tenders_unspsc_code ON tenders (unspsc_code);
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tenders_unspsc_code"), table_name="tenders")
    op.drop_index(op.f("ix_tenders_reference"), table_name="tenders")
    op.drop_column("tenders", "unspsc_code")
    op.drop_column("tenders", "current_phase")
    op.drop_column("tenders", "reference")
