"""PostgreSQL-backed persistence for maps SerpApi usage tracking.

Handles serpapi_usage table when DATABASE_URL is configured.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..settings import get_settings
from .postgres_athlete import _connect, _safe_close, has_postgres

_s = get_settings()
logger = logging.getLogger(__name__)


def _ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS serpapi_usage (
                month TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    conn.commit()


def get_usage(month: str | None = None) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    if month is None:
        month = datetime.now(UTC).strftime("%Y-%m")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT count FROM serpapi_usage WHERE month = %s", (month,))
            row = cur.fetchone()
            return int(row["count"]) if row else 0
    finally:
        _safe_close(conn)


def record_call(month: str | None = None, n: int = 1) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    if month is None:
        month = datetime.now(UTC).strftime("%Y-%m")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO serpapi_usage (month, count) VALUES (%s, %s)
                   ON CONFLICT(month) DO UPDATE SET count = serpapi_usage.count + excluded.count""",
                (month, n),
            )
            conn.commit()
    finally:
        _safe_close(conn)


__all__ = ["get_usage", "record_call"]
