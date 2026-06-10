FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package.json ./frontend/
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/frontend/dist/ /app/bike_analyzer/backend/static/

RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/rides.db

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]