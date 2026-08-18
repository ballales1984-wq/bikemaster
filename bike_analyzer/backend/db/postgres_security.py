"""PostgreSQL-backed persistence for revoked JWT tokens.

Handles revoked_tokens table when DATABASE_URL is configured.
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
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                revoked_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
    conn.commit()


def revoke_token(jti: str, ttl: int = 7200) -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO revoked_tokens (jti, revoked_at, expires_at)
                   VALUES (%s, %s, %s)
                   ON CONFLICT(jti) DO UPDATE SET revoked_at = excluded.revoked_at""",
                (jti, datetime.now(UTC).isoformat(),
                 (datetime.now(UTC) + __import__("datetime").timedelta(seconds=ttl)).isoformat()),
            )
            conn.commit()
    finally:
        _safe_close(conn)


def is_token_revoked(jti: str) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT expires_at FROM revoked_tokens WHERE jti = %s", (jti,))
            row = cur.fetchone()
            if not row:
                return False
            expires_at = datetime.fromisoformat(row["expires_at"])
            return datetime.now(UTC) < expires_at
    finally:
        _safe_close(conn)


def sweep_revoked_tokens() -> None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM revoked_tokens WHERE expires_at < %s", (datetime.now(UTC).isoformat(),))
            conn.commit()
    finally:
        _safe_close(conn)


__all__ = ["revoke_token", "is_token_revoked", "sweep_revoked_tokens"]
