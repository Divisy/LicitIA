#!/bin/bash
# Script to run migrations before starting the server in Railway

set -e  # Exit on error

echo "=========================================="
echo "LICITIA BACKEND INIT SCRIPT"
echo "=========================================="

echo "Running database migrations..."
alembic upgrade head

echo "Ensuring MVP SECOP columns exist on tenders..."
python <<'EOF'
import os
import sys
from sqlalchemy import create_engine, text

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL is not set")
    sys.exit(1)

engine = create_engine(database_url)
with engine.begin() as conn:
    conn.execute(text('ALTER TABLE tenders ADD COLUMN IF NOT EXISTS "reference" VARCHAR(255)'))
    conn.execute(text('ALTER TABLE tenders ADD COLUMN IF NOT EXISTS current_phase VARCHAR(200)'))
    conn.execute(text('ALTER TABLE tenders ADD COLUMN IF NOT EXISTS unspsc_code VARCHAR(50)'))
    conn.execute(text('ALTER TABLE tenders ADD COLUMN IF NOT EXISTS portfolio_id VARCHAR(100)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_tenders_portfolio_id ON tenders (portfolio_id)'))
    conn.execute(text('ALTER TABLE tenders ADD COLUMN IF NOT EXISTS documents_extraction_attempted_at TIMESTAMP'))
    conn.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_tenders_documents_extraction_attempted_at '
        'ON tenders (documents_extraction_attempted_at)'
    ))
    conn.execute(text(
        """
        UPDATE tenders
        SET documents_extraction_attempted_at = COALESCE(updated_at, created_at, NOW())
        WHERE documents_extraction_attempted_at IS NULL
          AND id IN (SELECT DISTINCT tender_id FROM tender_documents)
        """
    ))

    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS tender_documents (
            id UUID PRIMARY KEY,
            tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
            external_document_id VARCHAR(100) NOT NULL,
            document_type VARCHAR(50) NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            file_path VARCHAR(1000) NOT NULL,
            download_url VARCHAR(2000) NOT NULL,
            file_size BIGINT,
            extension VARCHAR(20),
            description TEXT,
            downloaded_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT uq_tender_document UNIQUE (tender_id, external_document_id)
        )
        """
    ))
    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_tender_documents_tender_id ON tender_documents (tender_id)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_tender_documents_external_document_id ON tender_documents (external_document_id)'))
    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_tender_documents_document_type ON tender_documents (document_type)'))

    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'tenders'
              AND column_name IN ('reference', 'current_phase', 'unspsc_code', 'portfolio_id')
            """
        )
    ).fetchall()
    columns = sorted(row[0] for row in rows)
    print(f"Tender columns present: {columns}")
    if len(columns) < 4:
        raise RuntimeError(f"Missing tender columns. Found: {columns}")

    table_exists = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'tender_documents'
            )
            """
        )
    ).scalar()
    print(f"tender_documents table present: {table_exists}")
    if not table_exists:
        raise RuntimeError("tender_documents table was not created")

EOF

echo "Migrations completed successfully"

DOCS_PATH="${DOCUMENTS_STORAGE_PATH:-storage/documents}"
mkdir -p "$DOCS_PATH"
echo "Document storage ready at: $DOCS_PATH"

echo "=========================================="
echo "Starting FastAPI server..."
echo "=========================================="

# Start uvicorn with explicit configuration
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info \
    --access-log

