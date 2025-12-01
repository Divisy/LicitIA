#!/bin/bash
# Script to run migrations before starting the server in Railway

set -e  # Exit on error

echo "=========================================="
echo "LICITIA BACKEND INIT SCRIPT"
echo "=========================================="

echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully"

echo "=========================================="
echo "Starting FastAPI server..."
echo "=========================================="

# Start uvicorn with explicit configuration
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info \
    --access-log

