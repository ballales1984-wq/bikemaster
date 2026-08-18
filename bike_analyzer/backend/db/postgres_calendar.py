"""PostgreSQL-backed persistence for calendar events.

When ``DATABASE_URL`` is configured (production on Render) calendar events
must live on the managed PostgreSQL database, not on the ephemeral
container-local SQLite file. On SQLite (local / offline) the synchronous
layer in ``database.py`` is still the authoritative store; this module is
only ever invoked through the thin dispatch guards added at the top of the
``database.py`` functions.

The public function names mirror ``database.py`` 1:1 so the routes keep
importing the same symbols. All column sets, defaults and return shapes are
deliberately aligned with the SQLite implementation so the two stores stay
swap-compatible.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_calendar_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER NOT NULL,
                tenant_id INTEGER DEFAULT 0,
                title TEXT NOT NULL,
                event_type TEXT DEFAULT 'training',
                date TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 0,
                description TEXT,
                completed BOOLEAN DEFAULT FALSE,
                weather_temp REAL,
                weather_humidity REAL,
                weather_description TEXT,
                created_at TEXT NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_calendar_athlete_date "
            "ON calendar_events(athlete_id, date)"
        )
        conn.commit()


def _row_to_calendar_event(row) -> dict:
    return {
        "id": row["id"],
        "athlete_id": row["athlete_id"],
        "tenant_id": row["tenant_id"],
        "title": row["title"],
        "event_type": row["event_type"],
        "date": row["date"],
        "duration_minutes": row["duration_minutes"],
        "description": row["description"],
        "completed": bool(row["completed"]),
        "weather_temp": row["weather_temp"],
        "weather_humidity": row["weather_humidity"],
        "weather_description": row["weather_description"],
        "created_at": row["created_at"],
    }


def save_calendar_event(event: dict, tenant_id: int = 0) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calendar_events
                (athlete_id, title, event_type, date, duration_minutes,
                 description, completed, weather_temp, weather_humidity,
                 weather_description, created_at, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    event.get("athlete_id"),
                    event.get("title"),
                    event.get("event_type", "training"),
                    event.get("date"),
                    event.get("duration_minutes", 0),
                    event.get("description"),
                    bool(event.get("completed")),
                    event.get("weather_temp"),
                    event.get("weather_humidity"),
                    event.get("weather_description"),
                    datetime.now(UTC).isoformat(),
                    event.get("tenant_id", tenant_id),
                ),
            )
            returning = cur.fetchone()
            conn.commit()
            return returning["id"] if returning else 0
    finally:
        _safe_close(conn)


def get_calendar_event(event_id: int) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM calendar_events WHERE id = %s", (event_id,))
            row = cur.fetchone()
            if row:
                return _row_to_calendar_event(row)
            return None
    finally:
        _safe_close(conn)


def get_events_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM calendar_events WHERE athlete_id = %s AND tenant_id = %s ORDER BY date DESC",
                    (athlete_id, tenant_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM calendar_events WHERE athlete_id = %s ORDER BY date DESC",
                    (athlete_id,),
                )
            rows = cur.fetchall()
            return [_row_to_calendar_event(r) for r in rows]
    finally:
        _safe_close(conn)


def get_events_by_date_range(
    athlete_id: int, start_date: str, end_date: str, tenant_id: int | None = None
) -> list[dict]:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    "SELECT * FROM calendar_events WHERE athlete_id = %s AND tenant_id = %s "
                    "AND date >= %s AND date <= %s ORDER BY date ASC",
                    (athlete_id, tenant_id, start_date, end_date),
                )
            else:
                cur.execute(
                    "SELECT * FROM calendar_events WHERE athlete_id = %s "
                    "AND date >= %s AND date <= %s ORDER BY date ASC",
                    (athlete_id, start_date, end_date),
                )
            rows = cur.fetchall()
            return [_row_to_calendar_event(r) for r in rows]
    finally:
        _safe_close(conn)


def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int | None = None) -> list[dict]:
    next_month = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    month_start = f"{year}-{month:02d}-01"
    return get_events_by_date_range(athlete_id, month_start, next_month, tenant_id)


def update_calendar_event(event_id: int, event_data: dict, tenant_id: int | None = None) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        existing = get_calendar_event(event_id)
        if not existing:
            return False
        merged = {**existing, **event_data}
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    """UPDATE calendar_events
                    SET title=%s, event_type=%s, date=%s, duration_minutes=%s,
                    description=%s, completed=%s, weather_temp=%s, weather_humidity=%s,
                    weather_description=%s WHERE id=%s AND tenant_id=%s""",
                    (
                        merged.get("title"),
                        merged.get("event_type", "training"),
                        merged.get("date"),
                        merged.get("duration_minutes", 0),
                        merged.get("description"),
                        bool(merged.get("completed")),
                        merged.get("weather_temp"),
                        merged.get("weather_humidity"),
                        merged.get("weather_description"),
                        event_id,
                        tenant_id,
                    ),
                )
            else:
                cur.execute(
                    """UPDATE calendar_events
                    SET title=%s, event_type=%s, date=%s, duration_minutes=%s,
                    description=%s, completed=%s, weather_temp=%s, weather_humidity=%s,
                    weather_description=%s WHERE id=%s""",
                    (
                        merged.get("title"),
                        merged.get("event_type", "training"),
                        merged.get("date"),
                        merged.get("duration_minutes", 0),
                        merged.get("description"),
                        bool(merged.get("completed")),
                        merged.get("weather_temp"),
                        merged.get("weather_humidity"),
                        merged.get("weather_description"),
                        event_id,
                    ),
                )
            conn.commit()
            return cur.rowcount > 0
    finally:
        _safe_close(conn)


def delete_calendar_event(event_id: int, tenant_id: int | None = None) -> bool:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_calendar_tables(conn)
        with conn.cursor() as cur:
            if tenant_id is not None:
                cur.execute("DELETE FROM calendar_events WHERE id = %s AND tenant_id = %s", (event_id, tenant_id))
            else:
                cur.execute("DELETE FROM calendar_events WHERE id = %s", (event_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
    finally:
        _safe_close(conn)
