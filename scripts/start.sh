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

# Start the server (foreground — Render tracks this PID)
# Migrations are handled by the app's background init_async_db() (CREATE TABLE IF NOT EXISTS)
# and optionally by run_migrations_on_startup() gated by RUN_MIGRATIONS_ON_STARTUP=0.
exec python main.py api --port ${PORT}
