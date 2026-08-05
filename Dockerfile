# === Build Stage ===
# Rebuild trigger - OAuth callback popup fix
ARG CACHEBUST=1
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
ENV PATH="./node_modules/.bin:$PATH"
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/src/ ./src/
COPY frontend/*.json ./
COPY frontend/*.js ./
COPY frontend/*.html ./
COPY frontend/public/ ./public/
COPY frontend/scripts/ ./scripts/
RUN npm run build

# === Production Stage ===
FROM python:3.11-slim AS production

# Cache bust — forces rebuild of COPY layers below when migration files change
ARG CACHEBUST=4
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MALLOC_TRIM_THRESHOLD_=65536

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r bikemaster && useradd -r -g bikemaster bikemaster

WORKDIR /app

COPY requirements.txt ./
COPY aethermap ./aethermap
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN echo "cache-bust=${CACHEBUST}" > /dev/null
COPY main.py ./
COPY bike_analyzer ./bike_analyzer
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts/ ./scripts/

RUN chown -R bikemaster:bikemaster /app && \
    python -m compileall bike_analyzer 2>/dev/null; \
    echo "Bytecode pre-compilation complete"

USER bikemaster

ENV SENTRY_DSN="" \
    SENTRY_ENVIRONMENT=production \
    SENTRY_TRACES_SAMPLE_RATE=0.2 \
    LOG_LEVEL=WARNING \
    UVICORN_WORKERS=1 \
    RUN_MIGRATIONS_ON_STARTUP=0

EXPOSE 10000

CMD ["bash", "scripts/start.sh"]
