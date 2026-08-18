"""Weather repository — SQLite persistence for weather cache."""

from __future__ import annotations

from datetime import UTC, datetime

from ...utils.logger import get_logger
from ..dispatch import pg_dispatch

logger = get_logger(__name__)


def _get_db_connection():
    from ..database import get_db_connection

    return get_db_connection()


@pg_dispatch("bike_analyzer.backend.db.postgres_weather")
def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
    """Get cached weather data for coordinates and date."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT temperature, humidity, description, cached_at FROM weather_cache WHERE lat=? AND lon=? AND date=?",
            (lat, lon, date),
        )
        row = cur.fetchone()
        if row:
            return {
                "temperature": row[0],
                "humidity": row[1],
                "description": row[2],
                "cached_at": row[3],
            }
        return None


@pg_dispatch("bike_analyzer.backend.db.postgres_weather")
def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
    """Save weather data to cache."""
    with _get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO weather_cache
            (lat, lon, date, temperature, humidity, description, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                lat,
                lon,
                date,
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("description"),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid
