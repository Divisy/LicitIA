"""Persist match judgments and experience-fit confirmations.

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-11-11 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "x4y5z6a7b8c9"
down_revision: Union[str, None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS object_match_judgments (
            purpose VARCHAR(64) NOT NULL,
            model VARCHAR(100) NOT NULL,
            tender_digest VARCHAR(64) NOT NULL,
            experience_digest VARCHAR(64) NOT NULL,
            matched BOOLEAN NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (purpose, model, tender_digest, experience_digest)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS experience_fit_confirmations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_email VARCHAR(255) NOT NULL,
            tender_id UUID NOT NULL,
            experience_ids TEXT NOT NULL,
            confirmed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (owner_email, tender_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS experience_fit_confirmations")
    op.execute("DROP TABLE IF EXISTS object_match_judgments")
