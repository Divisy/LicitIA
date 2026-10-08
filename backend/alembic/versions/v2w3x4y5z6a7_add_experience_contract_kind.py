"""Store the contract type chosen on a company experience.

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-10-08 18:20:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS contract_kind VARCHAR(40)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS contract_kind")
