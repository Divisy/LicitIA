"""Store executed line items read from the completion acta.

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-10-09 12:56:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "w3x4y5z6a7b8"
down_revision: Union[str, None] = "v2w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE company_experiences ADD COLUMN IF NOT EXISTS acta_partidas TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE company_experiences DROP COLUMN IF EXISTS acta_partidas")
