"""add login_codes and lead onboarding_completed_at

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-10-06 16:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE leads
        ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMP;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS login_codes (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            code_hash VARCHAR(64) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            consumed_at TIMESTAMP,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_login_codes_email ON login_codes (email);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS login_codes;")
    op.execute("ALTER TABLE leads DROP COLUMN IF EXISTS onboarding_completed_at;")
