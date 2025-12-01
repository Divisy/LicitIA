FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy init script
COPY init_railway.sh .
RUN chmod +x init_railway.sh

# Expose port
EXPOSE 8000

# Run migrations and start the application
CMD ["./init_railway.sh"]

