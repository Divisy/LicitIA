"""ensure mvp secop columns exist on tenders

Revision ID: e1a2b3c4d5e6
Revises: d4f8a1b2c3e4
Create Date: 2026-08-15 17:05:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1a2b3c4d5e6"
down_revision: Union[str, None] = "d4f8a1b2c3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: safe if d4f8a1b2c3e4 partially applied or skipped on production.
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
    op.execute("DROP INDEX IF EXISTS ix_tenders_unspsc_code;")
    op.execute("DROP INDEX IF EXISTS ix_tenders_reference;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS unspsc_code;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS current_phase;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS reference;")
