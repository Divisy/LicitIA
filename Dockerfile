# Railway monorepo entrypoint — builds the backend service from repo root.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN chmod +x init_railway.sh

EXPOSE 8000

CMD ["./init_railway.sh"]
