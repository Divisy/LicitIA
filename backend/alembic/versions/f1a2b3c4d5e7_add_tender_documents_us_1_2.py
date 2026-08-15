"""Add portfolio_id and tender_documents for user story 1.2."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, None] = "e1a2b3c4d5e6"
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

    op.create_table(
        "tender_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_document_id", sa.String(length=100), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("download_url", sa.String(length=2000), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("extension", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tender_id", "external_document_id", name="uq_tender_document"),
    )
    op.create_index("ix_tender_documents_tender_id", "tender_documents", ["tender_id"])
    op.create_index("ix_tender_documents_external_document_id", "tender_documents", ["external_document_id"])
    op.create_index("ix_tender_documents_document_type", "tender_documents", ["document_type"])


def downgrade() -> None:
    op.drop_index("ix_tender_documents_document_type", table_name="tender_documents")
    op.drop_index("ix_tender_documents_external_document_id", table_name="tender_documents")
    op.drop_index("ix_tender_documents_tender_id", table_name="tender_documents")
    op.drop_table("tender_documents")
    op.execute("DROP INDEX IF EXISTS ix_tenders_portfolio_id;")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS portfolio_id;")
