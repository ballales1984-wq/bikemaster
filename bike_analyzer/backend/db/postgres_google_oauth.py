"""PostgreSQL-backed persistence for Google OAuth tokens.

Handles google_tokens table when DATABASE_URL is configured.
"""
from __future__ import annotations

import logging

from ..settings import get_settings
from .postgres_athlete import _connect, _safe_close, has_postgres

_s = get_settings()
logger = logging.getLogger(__name__)


def _ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS google_tokens (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                provider TEXT NOT NULL CHECK(provider IN ('google_fit','google_health')),
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER,
                scope TEXT,
                created_at TEXT DEFAULT (now()),
                updated_at TEXT DEFAULT (now()),
                UNIQUE(athlete_id, provider)
            )
            """
        )
    conn.commit()


def save_google_token(athlete_id: int, provider: str, access_token: str,
                      refresh_token: str, expires_at: int = 0, scope: str = "") -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO google_tokens (athlete_id, provider, access_token, refresh_token, expires_at, scope)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT(athlete_id, provider) DO UPDATE SET
                       access_token = excluded.access_token,
                       refresh_token = excluded.refresh_token,
                       expires_at = excluded.expires_at,
                       scope = excluded.scope,
                       updated_at = now()
                   RETURNING id""",
                (athlete_id, provider, access_token, refresh_token, expires_at, scope),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_google_token(athlete_id: int, provider: str) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT access_token, refresh_token, expires_at, scope "
                "FROM google_tokens WHERE athlete_id = %s AND provider = %s",
                (athlete_id, provider),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
    finally:
        _safe_close(conn)


def delete_google_token(athlete_id: int, provider: str) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM google_tokens WHERE athlete_id = %s AND provider = %s", (athlete_id, provider))
            conn.commit()
    finally:
        _safe_close(conn)


__all__ = ["save_google_token", "get_google_token", "delete_google_token"]
