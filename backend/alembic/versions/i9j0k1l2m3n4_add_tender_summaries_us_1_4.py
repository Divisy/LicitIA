"""Add tender_summaries table for US 1.4."""

from typing import Sequence, Union

from alembic import op


revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tender_summaries (
            tender_id UUID PRIMARY KEY REFERENCES tenders(id) ON DELETE CASCADE,
            contract_kind VARCHAR(50) NOT NULL DEFAULT 'desconocido',
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            extracted_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tender_summaries_contract_kind
        ON tender_summaries (contract_kind);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tender_summaries_contract_kind;")
    op.execute("DROP TABLE IF EXISTS tender_summaries;")
