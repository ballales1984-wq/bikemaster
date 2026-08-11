"""Calendar repository — SQLite persistence for calendar events."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..database import get_db_connection

logger = get_logger(__name__)


def _row_to_calendar_event(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []

    def _col(name, default=None):
        return row[name] if name in keys else default

    return {
        "id": _col("id"),
        "athlete_id": _col("athlete_id", 0),
        "tenant_id": _col("tenant_id", 0),
        "title": _col("title"),
        "event_type": _col("event_type", "training"),
        "date": _col("date"),
        "duration_minutes": _col("duration_minutes", 0),
        "description": _col("description"),
        "completed": bool(_col("completed", False)),
        "weather_temp": _col("weather_temp"),
        "weather_humidity": _col("weather_humidity"),
        "weather_description": _col("weather_description"),
        "created_at": _col("created_at"),
    }


def save_calendar_event(event: dict, tenant_id: int = 0) -> int:
    weather = {}
    if event.get("lat") is not None and event.get("lon") is not None:
        try:
            from ..weather.weather_service import get_forecast_for_date

            weather = get_forecast_for_date(float(event["lat"]), float(event["lon"]), event.get("date", ""))
            if "error" in weather:
                weather = {}
        except Exception:
            weather = {}

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO calendar_events
            (athlete_id, title, event_type, date, duration_minutes,
             description, completed, weather_temp, weather_humidity,
             weather_description, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.get("athlete_id"),
                event.get("title"),
                event.get("event_type", "training"),
                event.get("date"),
                event.get("duration_minutes", 0),
                event.get("description"),
                1 if event.get("completed") else 0,
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("description"),
                datetime.now(UTC).isoformat(),
                event.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_calendar_event(event_id: int) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        if row:
            return _row_to_calendar_event(row)
        return None


def get_events_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND tenant_id = ? ORDER BY date DESC",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? ORDER BY date DESC",
                (athlete_id,),
            )
        rows = cur.fetchall()
        return [_row_to_calendar_event(r) for r in rows]


def get_events_by_date_range(
    athlete_id: int, start_date: str, end_date: str, tenant_id: int | None = None
) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND tenant_id = ? "
                "AND date >= ? AND date <= ? ORDER BY date ASC",
                (athlete_id, tenant_id, start_date, end_date),
            )
        else:
            cur.execute(
                "SELECT * FROM calendar_events WHERE athlete_id = ? AND date >= ? AND date <= ? ORDER BY date ASC",
                (athlete_id, start_date, end_date),
            )
        rows = cur.fetchall()
        return [_row_to_calendar_event(r) for r in rows]


def get_events_by_month(athlete_id: int, year: int, month: int, tenant_id: int | None = None) -> list[dict]:
    next_month = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    month_start = f"{year}-{month:02d}-01"
    return get_events_by_date_range(athlete_id, month_start, next_month, tenant_id)


def update_calendar_event(event_id: int, event_data: dict, tenant_id: int | None = None) -> bool:
    existing = get_calendar_event(event_id)
    if not existing:
        return False
    merged = {**existing, **event_data}
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                """UPDATE calendar_events
                SET title=?, event_type=?, date=?, duration_minutes=?,
                description=?, completed=?, weather_temp=?, weather_humidity=?,
                weather_description=? WHERE id=? AND tenant_id=?""",
                (
                    merged.get("title"),
                    merged.get("event_type", "training"),
                    merged.get("date"),
                    merged.get("duration_minutes", 0),
                    merged.get("description"),
                    1 if merged.get("completed") else 0,
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
                SET title=?, event_type=?, date=?, duration_minutes=?,
                description=?, completed=?, weather_temp=?, weather_humidity=?,
                weather_description=? WHERE id=?""",
                (
                    merged.get("title"),
                    merged.get("event_type", "training"),
                    merged.get("date"),
                    merged.get("duration_minutes", 0),
                    merged.get("description"),
                    1 if merged.get("completed") else 0,
                    merged.get("weather_temp"),
                    merged.get("weather_humidity"),
                    merged.get("weather_description"),
                    event_id,
                ),
            )
        conn.commit()
        return cur.rowcount > 0


def delete_calendar_event(event_id: int, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM calendar_events WHERE id = ? AND tenant_id = ?", (event_id, tenant_id))
        else:
            cur.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
