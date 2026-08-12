"""PostgreSQL-backed persistence for chat messages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_chat_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                tenant_id INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_chat_history_athlete_id
            ON chat_history(athlete_id)
            """
        )
        conn.commit()


def save_chat_message(athlete_id: int | None, role: str, content: str, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_chat_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (athlete_id, role, content, created_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (athlete_id, role, content, datetime.now(UTC).isoformat(), tenant_id),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)


def get_chat_history(athlete_id: int, limit: int = 10, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_chat_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT role, content, created_at FROM chat_history "
                    "WHERE athlete_id = %s AND tenant_id = %s ORDER BY id DESC LIMIT %s",
                    (athlete_id, tenant_id, limit),
                )
            else:
                cur.execute(
                    "SELECT role, content, created_at FROM chat_history WHERE athlete_id = %s ORDER BY id DESC LIMIT %s",
                    (athlete_id, limit),
                )
            rows = cur.fetchall()
        return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows]
    finally:
        _safe_close(conn)


def clear_chat_history(athlete_id: int, tenant_id: int | None = None) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_chat_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "DELETE FROM chat_history WHERE athlete_id = %s AND tenant_id = %s",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "DELETE FROM chat_history WHERE athlete_id = %s",
                    (athlete_id,),
                )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def prune_chat_history(athlete_id: int, tenant_id: int | None = None, retention_days: int = 90) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_chat_tables(conn)
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "DELETE FROM chat_history WHERE athlete_id = %s AND tenant_id = %s AND created_at < %s",
                    (athlete_id, tenant_id, cutoff.isoformat()),
                )
            else:
                cur.execute(
                    "DELETE FROM chat_history WHERE athlete_id = %s AND created_at < %s",
                    (athlete_id, cutoff.isoformat()),
                )
            conn.commit()
            return cur.rowcount
    finally:
        _safe_close(conn)
