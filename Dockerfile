FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/rides.db

CMD ["sh", "-c", "python main.py api --port ${PORT:-8000}"]