"""Database layer - supports SQLite (local) and PostgreSQL (production)."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

from ..models.models import Ride
from ..settings import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

_s = get_settings()
DB_PATH = _s.db_path
_INITIAL_DB_PATH = DB_PATH


@contextmanager
def get_db_connection():
    """Context manager for database connections with WAL mode and retry."""
    import time

    max_retries = 3
    retry_delay = 0.1
    conn = None
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            break
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise

    if conn is None:
        raise RuntimeError(f"Failed to connect to database at {DB_PATH} after {max_retries} retries")

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            distance_km REAL DEFAULT 0,
            duration_minutes REAL DEFAULT 0,
            avg_speed_kmh REAL DEFAULT 0,
            weight_kg REAL DEFAULT 70,
            calories REAL DEFAULT 0,
            heart_rate_avg REAL,
            elevation_gain_m REAL,
            gps_points TEXT,
            created_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            picture TEXT,
            age INTEGER DEFAULT 30,
            weight_kg REAL DEFAULT 70,
            height_cm REAL,
            fat_percentage REAL,
            years_active INTEGER DEFAULT 1,
            weekly_sessions INTEGER DEFAULT 3,
            monthly_hours REAL DEFAULT 0,
            annual_hours REAL DEFAULT 0,
            experience_level TEXT DEFAULT 'Beginner',
            goals TEXT,
            preferred_terrain TEXT,
            weekly_volume_km REAL DEFAULT 0,
            best_segments TEXT,
            medical_notes TEXT,
            equipment TEXT,
            ftp_watts REAL,
            password_hash TEXT,
            tenant_id INTEGER DEFAULT 0,
            created_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            tenant_id INTEGER DEFAULT 0,
            title TEXT NOT NULL,
            event_type TEXT DEFAULT 'training',
            date TEXT NOT NULL,
            duration_minutes INTEGER DEFAULT 0,
            description TEXT,
            completed INTEGER DEFAULT 0,
            weather_temp REAL,
            weather_humidity REAL,
            weather_description TEXT,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            date TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            description TEXT,
            cached_at TEXT,
            UNIQUE(lat, lon, date)
        )""")
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(athletes)")
        athlete_cols = [row[1] for row in cur.fetchall()]
        if "goals" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN goals TEXT")
        if "ftp_watts" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN ftp_watts REAL")
        if "password_hash" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN password_hash TEXT")
        if "email" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN email TEXT")
        if "picture" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN picture TEXT")
        conn.execute("""CREATE TABLE IF NOT EXISTS training_stress_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            tss REAL,
            atl REAL,
            ctl REAL,
            tsb REAL,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(athlete_id, date),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER,
            ride_id INTEGER,
            fatigue_score REAL,
            recovery_hours REAL,
            calories_per_km REAL,
            efficiency_score REAL,
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (ride_id) REFERENCES rides(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
        conn.execute("""CREATE TABLE IF NOT EXISTS training_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            title TEXT NOT NULL,
            description TEXT,
            goal_type TEXT DEFAULT 'granfondo',
            target_date TEXT,
            target_distance_km REAL,
            target_elevation_m REAL,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS planned_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            tenant_id INTEGER DEFAULT 0,
            goal_id INTEGER,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            workout_type TEXT DEFAULT 'endurance',
            duration_minutes INTEGER DEFAULT 60,
            target_intensity REAL DEFAULT 0.5,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (athlete_id) REFERENCES athletes(id),
            FOREIGN KEY (goal_id) REFERENCES training_goals(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS road_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            incident_date TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            description TEXT,
            road_type TEXT,
            source TEXT NOT NULL DEFAULT 'local',
            created_at TEXT,
            UNIQUE(source_id, source)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS route_safety_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER,
            athlete_id INTEGER,
            risk_score REAL,
            label TEXT,
            advice TEXT,
            road_type_counts TEXT,
            has_bike_infrastructure INTEGER,
            incident_count INTEGER,
            route_length_km REAL,
            computed_at TEXT,
            tenant_id INTEGER DEFAULT 0,
            FOREIGN KEY (ride_id) REFERENCES rides(id),
            FOREIGN KEY (athlete_id) REFERENCES athletes(id)
         )""")
        conn.commit()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(rides)")
        ride_cols = [row[1] for row in cur.fetchall()]
        if "external_source" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN external_source TEXT")
        if "external_id" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN external_id TEXT")
        if "title" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN title TEXT")
        if "tenant_id" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN tenant_id INTEGER DEFAULT 0")
        if "weight_kg" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN weight_kg REAL DEFAULT 70")
        if "calories" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN calories REAL DEFAULT 0")
        if "heart_rate_avg" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN heart_rate_avg REAL")
        if "elevation_gain_m" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN elevation_gain_m REAL")
        if "gps_points" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN gps_points TEXT")
        if "created_at" not in ride_cols:
            conn.execute("ALTER TABLE rides ADD COLUMN created_at TEXT")
        cur.execute("PRAGMA table_info(athletes)")
        athlete_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in athlete_cols:
            conn.execute("ALTER TABLE athletes ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(chat_history)")
        chat_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in chat_cols:
            conn.execute("ALTER TABLE chat_history ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(calendar_events)")
        cal_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN tenant_id INTEGER DEFAULT 0")
        if "weather_temp" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_temp REAL")
        if "weather_humidity" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_humidity REAL")
        if "weather_description" not in cal_cols:
            conn.execute("ALTER TABLE calendar_events ADD COLUMN weather_description TEXT")
        cur.execute("PRAGMA table_info(training_stress_days)")
        stress_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in stress_cols:
            conn.execute("ALTER TABLE training_stress_days ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(metrics)")
        metric_cols = [row[1] for row in cur.fetchall()]
        if "athlete_id" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN athlete_id INTEGER")
        if "fatigue_score" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN fatigue_score REAL")
        if "recovery_hours" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN recovery_hours REAL")
        if "calories_per_km" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN calories_per_km REAL")
        if "efficiency_score" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN efficiency_score REAL")
        if "created_at" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN created_at TEXT")
        if "tenant_id" not in metric_cols:
            conn.execute("ALTER TABLE metrics ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(training_goals)")
        goal_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in goal_cols:
            conn.execute("ALTER TABLE training_goals ADD COLUMN tenant_id INTEGER DEFAULT 0")
        cur.execute("PRAGMA table_info(planned_workouts)")
        workout_cols = [row[1] for row in cur.fetchall()]
        if "tenant_id" not in workout_cols:
            conn.execute("ALTER TABLE planned_workouts ADD COLUMN tenant_id INTEGER DEFAULT 0")
        _ensure_external_identity_index(conn)
        conn.commit()


def _ensure_external_identity_index(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """SELECT COUNT(*) FROM (
            SELECT external_source, external_id, COUNT(*) AS duplicate_count
            FROM rides
            WHERE external_source IS NOT NULL AND external_id IS NOT NULL
            GROUP BY external_source, external_id
            HAVING COUNT(*) > 1
        )"""
    )
    if cur.fetchone()[0] == 0:
        conn.execute("DROP INDEX IF EXISTS ix_rides_external_source")
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS uq_rides_external_identity
            ON rides (external_source, external_id)"""
        )


def _row_to_ride(row) -> dict:
    try:
        gps = json.loads(row["gps_points"]) if row["gps_points"] else None
    except (json.JSONDecodeError, TypeError):
        gps = None
    keys = row.keys()
    return {
        "id": row["id"],
        "athlete_id": row["athlete_id"],
        "date": row["date"],
        "distance_km": row["distance_km"],
        "duration_minutes": row["duration_minutes"],
        "avg_speed_kmh": row["avg_speed_kmh"],
        "weight_kg": row["weight_kg"],
        "calories": row["calories"],
        "heart_rate_avg": row["heart_rate_avg"],
        "elevation_gain_m": row["elevation_gain_m"],
        "gps_points": gps,
        "created_at": row["created_at"],
        "external_source": row["external_source"] if "external_source" in keys else None,
        "external_id": row["external_id"] if "external_id" in keys else None,
        "title": row["title"] if "title" in keys else None,
        "tenant_id": row["tenant_id"] if "tenant_id" in keys else 0,
    }


def _find_existing_external_ride(conn, external_source: str | None, external_id: str | None) -> int | None:
    if not external_source or not external_id:
        return None
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM rides WHERE external_source = ? AND external_id = ? LIMIT 1",
        (str(external_source), str(external_id)),
    )
    row = cur.fetchone()
    return int(row["id"]) if row else None


def save_ride(ride: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        external_source = str(ride.get("external_source") or "").strip() or None
        external_id = str(ride.get("external_id") or "").strip() or None
        existing_ride_id = _find_existing_external_ride(conn, external_source, external_id)
        if existing_ride_id is not None:
            return existing_ride_id
        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        tenant_id = ride.get("tenant_id", ride.get("athlete_id", 0))
        cur.execute(
            """INSERT INTO rides
            (athlete_id, date, distance_km, duration_minutes, avg_speed_kmh,
             weight_kg, calories, heart_rate_avg, elevation_gain_m, gps_points,
             external_source, external_id, title, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ride.get("athlete_id"),
                ride.get("date"),
                ride.get("distance_km", 0),
                ride.get("duration_minutes", 0),
                ride.get("avg_speed_kmh", 0),
                ride.get("weight_kg", 70),
                ride.get("calories", 0),
                ride.get("heart_rate_avg"),
                ride.get("elevation_gain_m"),
                gps_points,
                external_source,
                external_id,
                ride.get("title"),
                datetime.now(UTC).isoformat(),
                tenant_id,
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_ride(ride_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
        row = cur.fetchone()
        if row:
            return _row_to_ride(row)
        return None


def get_rides_by_athlete(athlete_id: int, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]


def get_athlete_by_name(name: str, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE name = ? AND tenant_id = ?", (name, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


def get_athlete_by_email(email: str, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE email = ? AND tenant_id = ?", (email, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE email = ?", (email,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


def get_all_rides(athlete_id: int | None = None, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if athlete_id is not None and tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        elif athlete_id is not None:
            cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        elif tenant_id is not None:
            cur.execute("SELECT * FROM rides WHERE tenant_id = ?", (tenant_id,))
        else:
            cur.execute("SELECT * FROM rides")
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]


def get_paginated_rides(
    page: int = 1, page_size: int = 20, sort: str = "date", athlete_id: int | None = None, tenant_id: int | None = None
) -> tuple[list[dict], int]:
    """Get paginated rides with safe ORDER BY whitelist."""
    order_map = {
        "date": "date",
        "distance": "distance_km",
        "duration": "duration_minutes",
    }
    order_col = order_map.get(sort, "date")
    offset = (page - 1) * page_size
    with get_db_connection() as conn:
        cur = conn.cursor()
        if athlete_id is not None and tenant_id is not None:
            cur.execute("SELECT COUNT(*) FROM rides WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT * FROM rides WHERE athlete_id = ? AND tenant_id = ? "
                f"ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                (athlete_id, tenant_id, page_size, offset),
            )
        elif athlete_id is not None:
            cur.execute("SELECT COUNT(*) FROM rides WHERE athlete_id = ?", (athlete_id,))
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT * FROM rides WHERE athlete_id = ? ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                (athlete_id, page_size, offset),
            )
        elif tenant_id is not None:
            cur.execute("SELECT COUNT(*) FROM rides WHERE tenant_id = ?", (tenant_id,))
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT * FROM rides WHERE tenant_id = ? ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                (tenant_id, page_size, offset),
            )
        else:
            cur.execute("SELECT COUNT(*) FROM rides")
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT * FROM rides ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            )
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows], total


def delete_ride(ride_id: int, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM rides WHERE id = ? AND tenant_id = ?", (ride_id, tenant_id))
        else:
            cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


def update_ride(ride_id: int, ride: dict, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        ride_tenant_id = ride.get("tenant_id", tenant_id) or ride.get("athlete_id")
        if tenant_id is not None:
            cur.execute(
                """UPDATE rides SET athlete_id=?, date=?, distance_km=?,
                duration_minutes=?, avg_speed_kmh=?, weight_kg=?, calories=?,
                heart_rate_avg=?, elevation_gain_m=?, gps_points=?, tenant_id=? WHERE id=? AND tenant_id=?""",
                (
                    ride.get("athlete_id"),
                    ride.get("date"),
                    ride.get("distance_km", 0),
                    ride.get("duration_minutes", 0),
                    ride.get("avg_speed_kmh", 0),
                    ride.get("weight_kg", 70),
                    ride.get("calories", 0),
                    ride.get("heart_rate_avg"),
                    ride.get("elevation_gain_m"),
                    gps_points,
                    ride_tenant_id,
                    ride_id,
                    tenant_id,
                ),
            )
        else:
            cur.execute(
                """UPDATE rides SET athlete_id=?, date=?, distance_km=?,
                duration_minutes=?, avg_speed_kmh=?, weight_kg=?, calories=?,
                heart_rate_avg=?, elevation_gain_m=?, gps_points=?, tenant_id=? WHERE id=?""",
                (
                    ride.get("athlete_id"),
                    ride.get("date"),
                    ride.get("distance_km", 0),
                    ride.get("duration_minutes", 0),
                    ride.get("avg_speed_kmh", 0),
                    ride.get("weight_kg", 70),
                    ride.get("calories", 0),
                    ride.get("heart_rate_avg"),
                    ride.get("elevation_gain_m"),
                    gps_points,
                    ride_tenant_id,
                    ride_id,
                ),
            )
        conn.commit()
        return cur.rowcount > 0


def save_athlete(athlete: dict, athlete_id: int | None = None, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if athlete_id is None:
            cur.execute(
                """INSERT INTO athletes
                (name, email, picture, age, weight_kg, height_cm, fat_percentage,
                 years_active, weekly_sessions, monthly_hours, annual_hours,
                 experience_level, goals, preferred_terrain, weekly_volume_km,
                 best_segments, medical_notes, equipment, ftp_watts,
                 password_hash, tenant_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    athlete.get("name"),
                    athlete.get("email"),
                    athlete.get("picture"),
                    athlete.get("age"),
                    athlete.get("weight_kg", 70),
                    athlete.get("height_cm"),
                    athlete.get("fat_percentage"),
                    athlete.get("years_active", 1),
                    athlete.get("weekly_sessions", 3),
                    athlete.get("monthly_hours", 0),
                    athlete.get("annual_hours", 0),
                    athlete.get("experience_level", "Beginner"),
                    athlete.get("goals"),
                    athlete.get("preferred_terrain"),
                    athlete.get("weekly_volume_km", 0),
                    athlete.get("best_segments"),
                    athlete.get("medical_notes"),
                    athlete.get("equipment"),
                    athlete.get("ftp_watts"),
                    athlete.get("password_hash"),
                    athlete.get("tenant_id", tenant_id),
                    datetime.now(UTC).isoformat(),
                ),
            )
        else:
            cur.execute(
                """INSERT INTO athletes
                (id, name, email, picture, age, weight_kg, height_cm, fat_percentage,
                 years_active, weekly_sessions, monthly_hours, annual_hours,
                 experience_level, goals, preferred_terrain, weekly_volume_km,
                 best_segments, medical_notes, equipment, ftp_watts,
                 password_hash, tenant_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    athlete_id,
                    athlete.get("name"),
                    athlete.get("email"),
                    athlete.get("picture"),
                    athlete.get("age"),
                    athlete.get("weight_kg", 70),
                    athlete.get("height_cm"),
                    athlete.get("fat_percentage"),
                    athlete.get("years_active", 1),
                    athlete.get("weekly_sessions", 3),
                    athlete.get("monthly_hours", 0),
                    athlete.get("annual_hours", 0),
                    athlete.get("experience_level", "Beginner"),
                    athlete.get("goals"),
                    athlete.get("preferred_terrain"),
                    athlete.get("weekly_volume_km", 0),
                    athlete.get("best_segments"),
                    athlete.get("medical_notes"),
                    athlete.get("equipment"),
                    athlete.get("ftp_watts"),
                    athlete.get("password_hash"),
                    athlete.get("tenant_id", tenant_id),
                    datetime.now(UTC).isoformat(),
                ),
            )
        conn.commit()
        return cur.lastrowid


def _row_to_athlete(row) -> dict:
    """Convert athlete row to dict with dynamic column mapping."""
    if row is None:
        return None
    columns = [
        "id",
        "name",
        "email",
        "picture",
        "age",
        "weight_kg",
        "height_cm",
        "fat_percentage",
        "years_active",
        "weekly_sessions",
        "monthly_hours",
        "annual_hours",
        "experience_level",
        "goals",
        "preferred_terrain",
        "weekly_volume_km",
        "best_segments",
        "medical_notes",
        "equipment",
        "ftp_watts",
        "password_hash",
        "tenant_id",
        "created_at",
    ]
    keys = row.keys()
    return {col: row[col] if col in keys else None for col in columns}


def get_athlete(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("SELECT * FROM athletes WHERE id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
        row = cur.fetchone()
        if row:
            return _row_to_athlete(row)
        return None


def save_metric(metric: dict, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metrics
            (athlete_id, ride_id, fatigue_score, recovery_hours,
             calories_per_km, efficiency_score, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metric.get("athlete_id"),
                metric.get("ride_id"),
                metric.get("fatigue_score"),
                metric.get("recovery_hours"),
                metric.get("calories_per_km"),
                metric.get("efficiency_score"),
                datetime.now(UTC).isoformat(),
                metric.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    existing = get_athlete(athlete_id)
    if not existing:
        return False
    merged = {**existing, **athlete_data}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE athletes SET name=?, email=?, age=?, weight_kg=?,
            height_cm=?, fat_percentage=?, years_active=?, weekly_sessions=?,
            monthly_hours=?, annual_hours=?, experience_level=?, goals=?,
            preferred_terrain=?, weekly_volume_km=?, best_segments=?,
            medical_notes=?, equipment=?, ftp_watts=?, password_hash=?, tenant_id=? WHERE id=?""",
            (
                merged.get("name"),
                merged.get("email"),
                merged.get("age", 30),
                merged.get("weight_kg", 70),
                merged.get("height_cm"),
                merged.get("fat_percentage"),
                merged.get("years_active", 1),
                merged.get("weekly_sessions", 3),
                merged.get("monthly_hours", 0),
                merged.get("annual_hours", 0),
                merged.get("experience_level", "Beginner"),
                merged.get("goals"),
                merged.get("preferred_terrain"),
                merged.get("weekly_volume_km", 0),
                merged.get("best_segments"),
                merged.get("medical_notes"),
                merged.get("equipment"),
                merged.get("ftp_watts"),
                merged.get("password_hash"),
                merged.get("tenant_id", athlete_id),
                athlete_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


def create_indices():
    with get_db_connection() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_date ON rides(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_distance ON rides(distance_km)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_duration ON rides(duration_minutes)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_speed ON rides(avg_speed_kmh)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete ON rides(athlete_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
        _ensure_external_identity_index(conn)
        conn.commit()
    if DB_PATH != _INITIAL_DB_PATH:
        conn = sqlite3.connect(_INITIAL_DB_PATH)
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS rides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    athlete_id INTEGER,
                    tenant_id INTEGER DEFAULT 0,
                    date TEXT NOT NULL,
                    distance_km REAL DEFAULT 0,
                    duration_minutes REAL DEFAULT 0,
                    avg_speed_kmh REAL DEFAULT 0,
                    weight_kg REAL DEFAULT 70,
                    calories REAL DEFAULT 0,
                    heart_rate_avg REAL,
                    elevation_gain_m REAL,
                    gps_points TEXT,
                    external_source TEXT,
                    external_id TEXT,
                    title TEXT,
                    created_at TEXT
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    athlete_id INTEGER,
                    ride_id INTEGER,
                    fatigue_score REAL,
                    recovery_hours REAL,
                    calories_per_km REAL,
                    efficiency_score REAL,
                    created_at TEXT,
                    tenant_id INTEGER DEFAULT 0
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_date ON rides(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_distance ON rides(distance_km)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_duration ON rides(duration_minutes)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_speed ON rides(avg_speed_kmh)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete ON rides(athlete_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
            _ensure_external_identity_index(conn)
            conn.commit()
        finally:
            conn.close()


def backup_database(backup_path: str | None = None) -> str:
    import shutil
    from pathlib import Path

    if not Path(DB_PATH).exists():
        raise FileNotFoundError(f"Database {DB_PATH} does not exist yet")
    if backup_path is None:
        backup_path = f"rides_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def get_backup_dir() -> str:
    return os.path.join(os.path.dirname(DB_PATH), "backups")


def rotate_backups(max_backups: int = 10) -> list[str]:
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.startswith("rides_backup_") and f.endswith(".db")],
        reverse=True,
    )
    removed = []
    for old_backup in backups[max_backups:]:
        old_path = os.path.join(backup_dir, old_backup)
        os.remove(old_path)
        removed.append(old_backup)
    return removed


def scheduled_backup(max_backups: int = 10) -> dict[str, dict]:
    """Run a scheduled backup with rotation.

    Creates a timestamped backup in the backups/ directory and rotates old backups.
    Returns a dict with backup_path, backups_kept, and backups_removed.
    """
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"rides_backup_{timestamp}.db")
    backup_database(backup_path)
    removed = rotate_backups(max_backups)
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("rides_backup_")])
    logger.info("Scheduled backup completed: %s (kept %d, removed %d)", backup_path, len(backups), len(removed))
    return {
        "backup_path": backup_path,
        "backups_kept": len(backups),
        "backups_removed": len(removed),
        "removed_backups": removed,
    }


def save_chat_message(athlete_id: int | None, role: str, content: str, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO chat_history (athlete_id, role, content, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?)""",
            (athlete_id, role, content, datetime.now(UTC).isoformat(), tenant_id),
        )
        conn.commit()
        return cur.lastrowid


def get_chat_history(athlete_id: int, limit: int = 10, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
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


def clear_chat_history(athlete_id: int, tenant_id: int | None = None) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ? AND tenant_id = ?", (athlete_id, tenant_id))
        else:
            cur.execute("DELETE FROM chat_history WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0


def prune_chat_history(athlete_id: int, tenant_id: int | None = None, retention_days: int = 90) -> int:
    from datetime import datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    with get_db_connection() as conn:
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


def get_all_athletes() -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, experience_level FROM athletes")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "email": r[2], "experience_level": r[3]} for r in rows]


def save_calendar_event(event: dict, tenant_id: int = 0) -> int:
    weather = {}
    if event.get("lat") is not None and event.get("lon") is not None:
        from ..weather.weather_service import get_forecast_for_date

        try:
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
        "completed": _col("completed", False),
        "weather_temp": _col("weather_temp"),
        "weather_humidity": _col("weather_humidity"),
        "weather_description": _col("weather_description"),
        "created_at": _col("created_at"),
    }


def get_weather_cache(lat: float, lon: float, date: str) -> dict | None:
    """Get cached weather data for coordinates and date."""
    with get_db_connection() as conn:
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


def save_weather_cache(lat: float, lon: float, date: str, weather: dict) -> int:
    """Save weather data to cache."""
    with get_db_connection() as conn:
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


def upsert_training_stress_day(
    athlete_id: int, date: str, tss: float, atl: float, ctl: float, tsb: float, tenant_id: int = 0
) -> None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        now = datetime.now(UTC).isoformat()
        cur.execute(
            """INSERT INTO training_stress_days
            (athlete_id, date, tss, atl, ctl, tsb, created_at, updated_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
            tss=excluded.tss, atl=excluded.atl, ctl=excluded.ctl,
            tsb=excluded.tsb, updated_at=excluded.updated_at, tenant_id=excluded.tenant_id""",
            (athlete_id, date, tss, atl, ctl, tsb, now, now, tenant_id),
        )
        conn.commit()


def save_user(user: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, is_admin, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user.get("username"),
                user.get("email"),
                user.get("password_hash"),
                1 if user.get("is_admin") else 0,
                1 if user.get("is_active", True) else 0,
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with get_db_connection() as conn:
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
                "is_active": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7],
            }
        return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db_connection() as conn:
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
                "is_active": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7],
            }
        return None


def get_training_stress_days(athlete_id: int, limit: int = 90, tenant_id: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, tenant_id, limit),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT ?",
                (athlete_id, limit),
            )
        rows = cur.fetchall()
        return [{"date": r[0], "tss": r[1], "atl": r[2], "ctl": r[3], "tsb": r[4]} for r in rows]


def get_latest_training_stress(athlete_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? AND tenant_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT date, tss, atl, ctl, tsb "
                "FROM training_stress_days WHERE athlete_id = ? "
                "ORDER BY date DESC LIMIT 1",
                (athlete_id,),
            )
        row = cur.fetchone()
        if row:
            return {
                "date": row[0],
                "tss": row[1],
                "atl": row[2],
                "ctl": row[3],
                "tsb": row[4],
            }
        return None


def recalculate_training_stress_for_athlete(athlete_id: int, ftp: float = 250.0, tenant_id: int = 0) -> None:
    from ..analytics.training_stress import (
        estimate_tss,
        exponentially_weighted_moving_average,
    )

    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id, tenant_id)]
    if not rides:
        return
    daily: dict[str, float] = {}
    for ride in rides:
        tss = estimate_tss(ride, ftp=ftp)
        day = ride.date[:10] if ride.date else "unknown"
        daily[day] = daily.get(day, 0.0) + tss
    sorted_days = sorted(daily.items())
    tss_series = [v for _, v in sorted_days]
    atl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=7.0) for i in range(len(tss_series))
    ]
    ctl_series = [
        exponentially_weighted_moving_average(tss_series[: i + 1], tau_days=42.0) for i in range(len(tss_series))
    ]
    for i, (date_str, _) in enumerate(sorted_days):
        tsb = round(ctl_series[i] - atl_series[i], 1)
        upsert_training_stress_day(
            athlete_id,
            date_str,
            round(tss_series[i], 1),
            atl_series[i],
            ctl_series[i],
            tsb,
            tenant_id,
        )


def save_road_incident(incident: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO road_incidents
            (source_id, lat, lon, incident_date, severity, description,
             road_type, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(incident.get("id", incident.get("source_id", ""))),
                incident.get("lat"),
                incident.get("lon"),
                incident.get("date", incident.get("incident_date", "")),
                incident.get("severity", "medium"),
                incident.get("description", "")[:500],
                incident.get("road_type", ""),
                incident.get("source", "local"),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def save_route_safety_score(score_data: dict, tenant_id: int = 0) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO route_safety_scores
            (ride_id, athlete_id, risk_score, label, advice,
             road_type_counts, has_bike_infrastructure, incident_count,
             route_length_km, computed_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                score_data.get("ride_id"),
                score_data.get("athlete_id"),
                score_data.get("risk_score"),
                score_data.get("label"),
                score_data.get("advice"),
                json.dumps(score_data.get("road_type_counts", {})),
                1 if score_data.get("has_bike_infrastructure") else 0,
                score_data.get("incident_count", 0),
                score_data.get("route_length_km", 0),
                datetime.now(UTC).isoformat(),
                score_data.get("tenant_id", tenant_id),
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_route_safety_score(ride_id: int, tenant_id: int | None = None) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        if tenant_id is not None:
            cur.execute(
                "SELECT * FROM route_safety_scores WHERE ride_id = ? AND tenant_id = ? ORDER BY id DESC LIMIT 1",
                (ride_id, tenant_id),
            )
        else:
            cur.execute(
                "SELECT * FROM route_safety_scores WHERE ride_id = ? ORDER BY id DESC LIMIT 1",
                (ride_id,),
            )
        row = cur.fetchone()
        if row:
            return {
                "id": row[0],
                "ride_id": row[1],
                "athlete_id": row[2],
                "risk_score": row[3],
                "label": row[4],
                "advice": row[5],
                "road_type_counts": json.loads(row[6]) if row[6] else {},
                "has_bike_infrastructure": bool(row[7]),
                "incident_count": row[8],
                "route_length_km": row[9],
                "computed_at": row[10],
            }
        return None


def get_athlete_by_query(**query):
    """Backward-compatible alias expected by some tests.

    Example: get_athlete_by_query(name="...")
    """

    from .api_compat import get_athlete_by_query as _shim

    return _shim(get_athlete_by_name, **query)


__all__ = [
    "save_ride",
    "get_ride",
    "get_all_rides",
    "get_paginated_rides",
    "get_rides_by_athlete",
    "get_all_athletes",
    "delete_ride",
    "update_ride",
    "init_db",
    "save_athlete",
    "get_athlete",
    "get_athlete_by_name",
    "get_athlete_by_email",
    "get_athlete_by_query",
    "save_metric",
    "update_athlete",
    "create_indices",
    "backup_database",
    "get_db_connection",
    "save_chat_message",
    "get_chat_history",
    "clear_chat_history",
    "save_calendar_event",
    "get_calendar_event",
    "get_events_by_athlete",
    "get_events_by_date_range",
    "get_events_by_month",
    "update_calendar_event",
    "delete_calendar_event",
    "get_weather_cache",
    "save_weather_cache",
    "upsert_training_stress_day",
    "get_training_stress_days",
    "get_latest_training_stress",
    "recalculate_training_stress_for_athlete",
    "save_road_incident",
    "save_route_safety_score",
    "get_route_safety_score",
    "save_user",
    "get_user_by_username",
    "get_user_by_id",
]
