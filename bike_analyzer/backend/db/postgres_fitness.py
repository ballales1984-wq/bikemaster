"""PostgreSQL-backed persistence for fitness states."""

from __future__ import annotations

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_fitness_states_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fitness_states (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                date TEXT NOT NULL,
                fitness_state TEXT,
                computed_at TEXT
            )
            """
        )
        conn.commit()


def get_fitness_states_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_fitness_states_table(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM fitness_states WHERE athlete_id = %s AND tenant_id = %s ORDER BY date ASC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM fitness_states WHERE athlete_id = %s ORDER BY date ASC",
                    (athlete_id,),
                )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        _safe_close(conn)
