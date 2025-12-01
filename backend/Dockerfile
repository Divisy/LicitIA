FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements-base.txt .
COPY requirements.txt .

# Install base dependencies first (faster, change less frequently)
# This layer will be cached and reused if only code changes
RUN pip install --no-cache-dir -r requirements-base.txt

# Install ML dependencies (heavier, ~2GB, cached separately)
# This layer is cached separately, so it only rebuilds when ML deps change
RUN pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    scikit-learn==1.3.2 \
    torch==2.1.2 \
    torchvision==0.16.2 \
    transformers==4.35.2 \
    huggingface-hub==0.20.0

# Copy application code (this layer changes most frequently)
COPY . .

# Copy init script
COPY init_railway.sh .
RUN chmod +x init_railway.sh

# Expose port
EXPOSE 8000

# Run migrations and start the application
CMD ["./init_railway.sh"]

