FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/dist/assets bike_analyzer/backend/static/assets
COPY frontend/dist/index.html bike_analyzer/backend/static/index.html

COPY . .
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/rides.db

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]