"""PostgreSQL-backed persistence for the users domain.

When ``DATABASE_URL`` is configured (production on Render) the ``users`` table
must live on the *managed* PostgreSQL database, not on the ephemeral,
container-local SQLite file. This module is only ever invoked through the thin
dispatch guards added at the top of the ``database.py`` functions.

The public function names mirror ``database.py`` 1:1 so the routes keep
importing the same symbols. All column sets, defaults and return shapes are
deliberately aligned with the SQLite implementation so the two stores stay
swap-compatible.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ..settings import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)

# Reuse the connection / dispatch primitives defined once in postgres_athlete
# so there is a single source of truth for "is postgres configured" and for the
# psycopg2 connection factory.
from .postgres_athlete import _connect, _safe_close, has_postgres  # noqa: E402,F401


def _ensure_tables(conn) -> None:  # pragma: no cover - kept for standalone bootstrap
    """Best-effort ``CREATE TABLE IF NOT EXISTS`` fallback.

    On Render the tables are already created at startup by
    ``async_db.init_async_db`` (driven by the SQLAlchemy models in
    ``db/models.py``), so every statement here is a no-op. This only matters
    when the sync pg layer is used standalone (e.g. ad-hoc scripts).
    Uses PostgreSQL-native ``SERIAL`` (never SQLite ``AUTOINCREMENT``).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                is_admin INTEGER DEFAULT 0,
                is_client INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
    conn.commit()


def _dict_from_row(row) -> dict | None:
    if row is None:
        return None
    return dict(row)


def save_user(user: dict) -> int:
    now = datetime.now(UTC).isoformat()
    params = [
        user.get("username"),
        user.get("email"),
        user.get("password_hash"),
        1 if user.get("is_admin") else 0,
        1 if user.get("is_client") else 0,
        1 if user.get("is_active", True) else 0,
        now,
        now,
    ]
    cols = (
        "username, email, password_hash, is_admin, is_client, is_active, "
        "created_at, updated_at"
    )
    placeholders = ", ".join(["%s"] * len(params))
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO users ({cols}) VALUES ({placeholders}) RETURNING id",
                params,
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"]) if row else 0
    finally:
        _safe_close(conn)


def get_user_by_username(username: str) -> dict | None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "is_admin": bool(row["is_admin"]),
                    "is_client": bool(row["is_client"]),
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None
    finally:
        _safe_close(conn)


def get_user_by_id(user_id: int) -> dict | None:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "is_admin": bool(row["is_admin"]),
                    "is_client": bool(row["is_client"]),
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None
    finally:
        _safe_close(conn)


def get_all_users() -> list[dict]:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, is_admin, is_client, is_active, created_at, updated_at "
                "FROM users ORDER BY id DESC"
            )
            rows = cur.fetchall()
            return [
                {
                    "id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "is_admin": bool(row["is_admin"]),
                    "is_client": bool(row["is_client"]),
                    "is_active": bool(row["is_active"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
    finally:
        _safe_close(conn)


def update_user(user_id: int, updates: dict) -> dict | None:
    allowed = {"email", "password_hash", "is_admin", "is_client", "is_active"}
    fields = []
    values = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key in ("is_admin", "is_client", "is_active"):
            value = 1 if value else 0
        fields.append(f"{key} = %s")
        values.append(value)
    if not fields:
        return get_user_by_id(user_id)
    values.append(datetime.now(UTC).isoformat())
    values.append(user_id)
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(fields)}, updated_at = %s WHERE id = %s",
                values,
            )
            conn.commit()
        return get_user_by_id(user_id)
    finally:
        _safe_close(conn)


def delete_user(user_id: int) -> bool:
    conn = _connect()
    try:
        _ensure_tables(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


__all__ = [
    "has_postgres",
    "save_user",
    "get_user_by_username",
    "get_user_by_id",
    "get_all_users",
    "update_user",
    "delete_user",
]
