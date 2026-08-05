#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"

# Start the server immediately (foreground — Render tracks this PID).
# PostgreSQL connection, migrations, and SQLite init are handled asynchronously
# in app_factory.py background tasks, allowing uvicorn to open the HTTP port
# immediately so Render's port detection and healthcheck (/api/v1/health) succeed.
exec python main.py api --port ${PORT}

