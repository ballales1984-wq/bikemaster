"""Health Connect repository — SQLite persistence for Health Connect connections."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_health_connect")
def connect_health_connect(athlete_id: int, permissions: str = "[]") -> dict:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO health_connect_tokens (athlete_id, connected, permissions, created_at, updated_at)
               VALUES (?, 1, ?, ?, ?)
               ON CONFLICT(athlete_id) DO UPDATE SET
                   connected = 1,
                   permissions = excluded.permissions,
                   updated_at = excluded.updated_at""",
            (athlete_id, permissions, now, now),
        )
        conn.commit()
    return {"status": "connected", "permissions": permissions.split(",")}


@pg_dispatch("bike_analyzer.backend.db.postgres_health_connect")
def disconnect_health_connect(athlete_id: int) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM health_connect_tokens WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_health_connect")
def get_health_connect_token(athlete_id: int) -> dict | None:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT connected, permissions, last_sync_at FROM health_connect_tokens WHERE athlete_id = ?",
            (athlete_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "connected": bool(row[0]),
            "permissions": row[1],
            "last_sync_at": row[2],
        }


@pg_dispatch("bike_analyzer.backend.db.postgres_health_connect")
def update_health_connect_sync(athlete_id: int, last_sync_at: str) -> None:
    now = datetime.now(UTC).isoformat()
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE health_connect_tokens SET last_sync_at = ?, updated_at = ? WHERE athlete_id = ?",
            (last_sync_at, now, athlete_id),
        )
        conn.commit()
