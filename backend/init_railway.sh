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
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'tenders'
              AND column_name IN ('reference', 'current_phase', 'unspsc_code')
            """
        )
    ).fetchall()
    columns = sorted(row[0] for row in rows)
    print(f"MVP tender columns present: {columns}")
    if len(columns) < 3:
        raise RuntimeError(f"Missing MVP columns on tenders table. Found: {columns}")

EOF

echo "Migrations completed successfully"

mkdir -p storage/documents

echo "=========================================="
echo "Starting FastAPI server..."
echo "=========================================="

# Start uvicorn with explicit configuration
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info \
    --access-log

