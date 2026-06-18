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
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY bike_analyzer ./bike_analyzer

COPY --from=frontend-builder /app/frontend/dist ./bike_analyzer/backend/static

EXPOSE 8000

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]
