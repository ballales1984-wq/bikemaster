"""Chat repository — SQLite persistence for chat messages."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_chat")
def save_chat_message(athlete_id: int | None, role: str, content: str, tenant_id: int = 0) -> int:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO chat_history (athlete_id, role, content, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?)""",
            (athlete_id, role, content, datetime.now(UTC).isoformat(), tenant_id),
        )
        conn.commit()
        return cur.lastrowid


@pg_dispatch("bike_analyzer.backend.db.postgres_chat")
def get_chat_history(athlete_id: int, limit: int = 10, tenant_id: int | None = None) -> list[dict]:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT role, content, created_at FROM chat_history "
                "WHERE athlete_id = ? AND tenant_id = ? ORDER BY id DESC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT role, content, created_at FROM chat_history WHERE athlete_id = ? ORDER BY id DESC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]


@pg_dispatch("bike_analyzer.backend.db.postgres_chat")
def clear_chat_history(athlete_id: int, tenant_id: int | None = None) -> bool:
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


@pg_dispatch("bike_analyzer.backend.db.postgres_chat")
def prune_chat_history(athlete_id: int, tenant_id: int | None = None, retention_days: int = 90) -> int:
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    with _get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "DELETE FROM chat_history WHERE athlete_id = ? AND tenant_id = ? AND created_at < ?",
                (athlete_id, tenant_id, cutoff.isoformat()),
            )
        else:
            cur.execute(
                "DELETE FROM chat_history WHERE athlete_id = ? AND created_at < ?",
                (athlete_id, cutoff.isoformat()),
            )
        conn.commit()
        return cur.rowcount
