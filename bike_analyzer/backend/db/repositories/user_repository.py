"""User repository — SQLite persistence for users."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def save_user(user: dict) -> int:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, is_admin,
             is_client, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user.get("username"),
                user.get("email"),
                user.get("password_hash"),
                1 if user.get("is_admin") else 0,
                1 if user.get("is_client") else 0,
                1 if user.get("is_active", True) else 0,
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def get_user_by_username(username: str) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],
                "is_admin": bool(row[4]),
                "is_client": bool(row[5]),
                "is_active": bool(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def get_user_by_id(user_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "password_hash": row[3],
                "is_admin": bool(row[4]),
                "is_client": bool(row[5]),
                "is_active": bool(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
            }
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def get_all_users() -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, email, is_admin, is_client, is_active, "
            "created_at, updated_at FROM users ORDER BY id DESC"
        )
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "is_admin": bool(row[3]),
                "is_client": bool(row[4]),
                "is_active": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7],
            }
            for row in rows
        ]


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def update_user(user_id: int, updates: dict) -> dict | None:
    allowed = {"email", "password_hash", "is_admin", "is_client", "is_active"}
    fields = []
    values = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key in ("is_admin", "is_client", "is_active"):
            value = 1 if value else 0
        fields.append(f"{key} = ?")
        values.append(value)
    if not fields:
        return get_user_by_id(user_id)
    values.append(datetime.now(UTC).isoformat())
    values.append(user_id)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {', '.join(fields)}, updated_at = ? WHERE id = ?", values)
        conn.commit()
    return get_user_by_id(user_id)


@pg_dispatch("bike_analyzer.backend.db.postgres_users")
def delete_user(user_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
