"""Add documents_extraction_attempted_at for US 1.2.2 backfill tracking.

Revision ID: h8i9j0k1l2m3
Revises: g7a8b9c0d1e2
Create Date: 2026-08-17 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS documents_extraction_attempted_at TIMESTAMP;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tenders_documents_extraction_attempted_at
        ON tenders (documents_extraction_attempted_at);
        """
    )
    op.execute(
        """
        UPDATE tenders
        SET documents_extraction_attempted_at = COALESCE(updated_at, created_at, NOW())
        WHERE documents_extraction_attempted_at IS NULL
          AND id IN (SELECT DISTINCT tender_id FROM tender_documents);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tenders_documents_extraction_attempted_at;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS documents_extraction_attempted_at;")
