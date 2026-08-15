"""Ensure US 1.2 document schema exists on production.

Revision ID: g7a8b9c0d1e2
Revises: f1a2b3c4d5e7
Create Date: 2026-08-15 20:12:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "g7a8b9c0d1e2"
down_revision: Union[str, None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS portfolio_id VARCHAR(100);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tenders_portfolio_id ON tenders (portfolio_id);
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tender_documents (
            id UUID PRIMARY KEY,
            tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
            external_document_id VARCHAR(100) NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            file_path VARCHAR(1000) NOT NULL,
            download_url VARCHAR(2000) NOT NULL,
            file_size BIGINT,
            extension VARCHAR(20),
            description TEXT,
            downloaded_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT uq_tender_document UNIQUE (tender_id, external_document_id)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tender_documents_tender_id
        ON tender_documents (tender_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tender_documents_external_document_id
        ON tender_documents (external_document_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tender_documents_document_type
        ON tender_documents (document_type);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tender_documents_document_type;")
    op.execute("DROP INDEX IF EXISTS ix_tender_documents_external_document_id;")
    op.execute("DROP INDEX IF EXISTS ix_tender_documents_tender_id;")
    op.execute("DROP TABLE IF EXISTS tender_documents;")
    op.execute("DROP INDEX IF EXISTS ix_tenders_portfolio_id;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS portfolio_id;")
