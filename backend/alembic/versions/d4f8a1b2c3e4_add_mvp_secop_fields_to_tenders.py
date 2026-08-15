"""add mvp secop fields to tenders

Revision ID: d4f8a1b2c3e4
Revises: 924de1696ecd
Create Date: 2026-08-15 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a1b2c3e4"
down_revision: Union[str, None] = "b42030ef19cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenders", sa.Column("reference", sa.String(length=255), nullable=True))
    op.add_column("tenders", sa.Column("current_phase", sa.String(length=200), nullable=True))
    op.add_column("tenders", sa.Column("unspsc_code", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_tenders_reference"), "tenders", ["reference"], unique=False)
    op.create_index(op.f("ix_tenders_unspsc_code"), "tenders", ["unspsc_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenders_unspsc_code"), table_name="tenders")
    op.drop_index(op.f("ix_tenders_reference"), table_name="tenders")
    op.drop_column("tenders", "unspsc_code")
    op.drop_column("tenders", "current_phase")
    op.drop_column("tenders", "reference")
