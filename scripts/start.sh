#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"

# Wait for PostgreSQL if DATABASE_URL is set
if echo "${DATABASE_URL:-}" | grep -q "postgresql"; then
  echo "Waiting for PostgreSQL..."
  for i in $(seq 1 30); do
    if python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null; then
      echo "PostgreSQL is ready."
      break
    fi
    echo "PostgreSQL not ready yet (attempt $i/30)..."
    sleep 2
  done
fi

# Run alembic migrations with a hard timeout. If migrations fail or timeout,
# the server still starts — the app's init_async_db() will create tables
# via SQLAlchemy metadata.create_all() (idempotent with IF NOT EXISTS).
if [ -f "./alembic.ini" ]; then
  echo "Running alembic migrations (timeout 120s, SIGKILL)..."
  timeout --signal=KILL 120 alembic upgrade head 2>&1 || echo "Alembic failed or timed out; server will create tables via init_async_db()"
fi

# Start the server (foreground — Render tracks this PID)
exec python main.py api --port ${PORT}
