"""company_capacity for US 1.11 RUP import

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-10-02 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "l2m3n4o5p6q7"
down_revision: Union[str, None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS company_capacity (
            id UUID PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL UNIQUE,
            nit VARCHAR(32),
            razon_social VARCHAR(500),
            camara VARCHAR(255),
            issued_at DATE,
            valid_until DATE,
            cut_year INTEGER,
            liquidity NUMERIC(18, 6),
            indebtedness NUMERIC(18, 6),
            interest_coverage NUMERIC(18, 6),
            return_on_equity NUMERIC(18, 6),
            return_on_assets NUMERIC(18, 6),
            working_capital NUMERIC(18, 2),
            organizational_json TEXT,
            source_pdf_key VARCHAR(500),
            source_pdf_filename VARCHAR(255),
            extracted_text_chars INTEGER,
            warnings_json TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_company_capacity_company_name
        ON company_capacity (company_name);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS company_capacity;")
