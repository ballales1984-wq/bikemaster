# === Build Stage ===
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json ./frontend/
COPY frontend/ ./frontend/
RUN cd frontend && npm install --legacy-peer-deps --no-audit --no-fund && npm run build

# === Production Stage ===
FROM python:3.11-slim AS production

# Security: create non-root user
RUN groupadd --gid 1001 bikemaster && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home bikemaster

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Copy application code
COPY --chown=bikemaster:bikemaster . .
COPY --from=frontend-builder --chown=bikemaster:bikemaster /app/frontend/dist/ /app/bike_analyzer/backend/static/

# Create data directory with proper permissions
RUN mkdir -p /app/data && chown -R bikemaster:bikemaster /app/data

# Switch to non-root user
USER bikemaster

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/rides.db \
    AI_COACH_MODE=external \
    ENVIRONMENT=production

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]