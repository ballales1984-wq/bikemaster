"""PostgreSQL-backed persistence for weather cache."""

from __future__ import annotations

from datetime import UTC, datetime

from .postgres_athlete import _connect, _safe_close, has_postgres


def _ensure_weather_cache_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_cache (
                id SERIAL PRIMARY KEY,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                date TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                description TEXT,
                cached_at TEXT NOT NULL DEFAULT NOW(),
                UNIQUE(lat, lon, date)
            )
            """
        )
        conn.commit()


def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_weather_cache_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT temperature, humidity, description, cached_at FROM weather_cache WHERE lat = %s AND lon = %s AND date = %s",
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
    finally:
        _safe_close(conn)


def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
    if not has_postgres():
        raise RuntimeError("PostgreSQL not configured")
    conn = _connect()
    try:
        _ensure_weather_cache_table(conn)
        cached_at = datetime.now(UTC).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO weather_cache (lat, lon, date, temperature, humidity, description, cached_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(lat, lon, date) DO UPDATE SET
                    temperature = excluded.temperature,
                    humidity = excluded.humidity,
                    description = excluded.description,
                    cached_at = excluded.cached_at
                RETURNING id
                """,
                (
                    lat,
                    lon,
                    date,
                    weather.get("temperature"),
                    weather.get("humidity"),
                    weather.get("description"),
                    cached_at,
                ),
            )
            conn.commit()
            return cur.fetchone()[0]
    finally:
        _safe_close(conn)
