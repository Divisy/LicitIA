"""associate RUP and experiences to the registered user email

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-10-06 23:20:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255);"
    )
    op.execute(
        "ALTER TABLE company_capacity ADD COLUMN IF NOT EXISTS owner_email VARCHAR(255);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_company_experiences_owner_email ON company_experiences (owner_email);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_company_capacity_owner_email ON company_capacity (owner_email);"
    )
    op.execute(
        "ALTER TABLE company_capacity DROP CONSTRAINT IF EXISTS company_capacity_company_name_key;"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_company_capacity_owner_email
        ON company_capacity (owner_email)
        WHERE owner_email IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_company_capacity_owner_email;")
    op.execute("DROP INDEX IF EXISTS ix_company_capacity_owner_email;")
    op.execute("DROP INDEX IF EXISTS ix_company_experiences_owner_email;")
    op.execute("ALTER TABLE company_capacity DROP COLUMN IF EXISTS owner_email;")
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS owner_email;")
