# === Build Stage ===
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
ENV PATH="./node_modules/.bin:$PATH"
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/src/ ./src/
COPY frontend/*.json ./
COPY frontend/*.js ./
COPY frontend/*.html ./
RUN npm run build

# === Production Stage ===
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r bikemaster && useradd -r -g bikemaster bikemaster

WORKDIR /app

COPY requirements.txt ./
# Use uv for faster/better dependency resolution with complex graphs
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv pip install --system --prerelease=allow -r requirements.txt

COPY main.py ./
COPY bike_analyzer ./bike_analyzer

COPY --from=frontend-builder /app/frontend/dist ./bike_analyzer/backend/static

RUN chown -R bikemaster:bikemaster /app

USER bikemaster

ENV SENTRY_DSN=""
ENV SENTRY_ENVIRONMENT=production
ENV SENTRY_TRACES_SAMPLE_RATE=0.2

EXPOSE 8000

# Security: Healthcheck with curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Security hardening labels for docker-compose reference
LABEL security_profile="hardened" \
      security_no_new_privileges="true" \
      security_read_only="true" \
      security_tmpfs="/tmp:noexec,nosuid,size=64m"

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]
