"""PostgreSQL-backed persistence for Health Connect tokens.

Handles health_connect_tokens table when DATABASE_URL is configured.
"""
from __future__ import annotations

import logging

from ..settings import get_settings
from .postgres_athlete import _connect, _safe_close

_s = get_settings()
logger = logging.getLogger(__name__)


def _ensure_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS health_connect_tokens (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                connected INTEGER NOT NULL DEFAULT 1,
                permissions TEXT DEFAULT '[]',
                last_sync_at TEXT,
                created_at TEXT DEFAULT (now()),
                updated_at TEXT DEFAULT (now()),
                UNIQUE(athlete_id)
            )
            """
        )
    conn.commit()


def connect_health_connect(athlete_id: int, permissions: str = "[]") -> dict:
    _ensure_tables(_connect())
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO health_connect_tokens (athlete_id, connected, permissions)
                   VALUES (%s, 1, %s)
                   ON CONFLICT(athlete_id) DO UPDATE SET
                       connected = 1,
                       permissions = excluded.permissions,
                       updated_at = now()""",
                (athlete_id, permissions),
            )
            conn.commit()
        return {"status": "connected", "permissions": permissions.split(",")}
    finally:
        _safe_close(conn)


def disconnect_health_connect(athlete_id: int) -> None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM health_connect_tokens WHERE athlete_id = %s", (athlete_id,))
            conn.commit()
    finally:
        _safe_close(conn)


def get_health_connect_token(athlete_id: int) -> dict | None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT connected, permissions, last_sync_at FROM health_connect_tokens WHERE athlete_id = %s",
                (athlete_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "connected": bool(row["connected"]),
                "permissions": row["permissions"],
                "last_sync_at": row["last_sync_at"],
            }
    finally:
        _safe_close(conn)


def update_health_connect_sync(athlete_id: int, last_sync_at: str) -> None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE health_connect_tokens SET last_sync_at = %s, updated_at = now() WHERE athlete_id = %s",
                (last_sync_at, athlete_id),
            )
            conn.commit()
    finally:
        _safe_close(conn)


__all__ = ["connect_health_connect", "disconnect_health_connect",
           "get_health_connect_token", "update_health_connect_sync"]
