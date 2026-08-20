FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    curl \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
# This layer will be cached and reused if requirements.txt doesn't change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (this layer changes most frequently)
COPY . .

# Make init script executable
RUN chmod +x init_railway.sh

# Expose port
EXPOSE 8000

# Run migrations and start the application
CMD ["./init_railway.sh"]

