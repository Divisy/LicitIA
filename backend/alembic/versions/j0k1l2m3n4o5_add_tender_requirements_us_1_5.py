"""Add tender_requirements table for US 1.5."""
from alembic import op

revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tender_requirements (
            tender_id UUID PRIMARY KEY REFERENCES tenders(id) ON DELETE CASCADE,
            extraction_version VARCHAR(20) NOT NULL DEFAULT '1.5.1',
            requirements_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            extracted_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tender_requirements;")
