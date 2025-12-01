FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Split requirements into base and ML dependencies for better caching
# Install base dependencies first (faster, change less frequently)
COPY requirements-base.txt* requirements.txt .
RUN if [ -f requirements-base.txt ]; then \
        pip install --no-cache-dir -r requirements-base.txt; \
    else \
        pip install --no-cache-dir \
            fastapi==0.104.1 \
            uvicorn[standard]==0.24.0 \
            pydantic==2.5.0 \
            pydantic-settings==2.1.0 \
            sqlalchemy==2.0.23 \
            alembic==1.12.1 \
            psycopg2-binary==2.9.9 \
            apscheduler==3.10.4 \
            requests==2.31.0 \
            email-validator==2.1.0 \
            python-multipart==0.0.6 \
            pandas==2.1.3 \
            openpyxl==3.1.2; \
    fi

# Install ML dependencies (heavier, cached separately)
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    scikit-learn==1.3.2 \
    torch==2.1.2 \
    torchvision==0.16.2 \
    transformers==4.35.2 \
    huggingface-hub==0.20.0 || echo "ML dependencies optional"

# Copy application code (this layer changes most frequently)
COPY . .

# Copy init script
COPY init_railway.sh .
RUN chmod +x init_railway.sh

# Expose port
EXPOSE 8000

# Run migrations and start the application
CMD ["./init_railway.sh"]

