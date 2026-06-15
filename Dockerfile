# === Build Stage ===
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json ./frontend/
COPY frontend/ ./frontend/
RUN cd frontend && npm install --legacy-peer-deps --no-audit --no-fund && npm run build

# === Security Scan Stage ===
FROM python:3.11-slim AS security-scan
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY . .
RUN pip install bandit && bandit -r bike_analyzer -ll

# === Production Stage ===
FROM gcr.io/distroless/python3-debian12 AS production
# Distroless = no shell, no package manager, minimal attack surface

WORKDIR /app

# Copy Python dependencies from scan stage
COPY --from=security-scan /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY --chown=nonroot:nonroot . .
COPY --from=frontend-builder --chown=nonroot:nonroot /app/frontend/dist/ /app/bike_analyzer/backend/static/

# Create data directory with proper permissions
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"] || exit 1

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/rides.db \
    AI_COACH_MODE=external \
    ENVIRONMENT=production

# Distroless runs as non-root by default
CMD ["main.py", "api", "--port", "8000"]