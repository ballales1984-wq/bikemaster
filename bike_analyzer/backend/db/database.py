"""SQLite database layer (simple)."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timezone
import sqlite3
import json
from contextlib import contextmanager

from ..config import DB_PATH

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS rides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER,
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
        created_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT,
        FOREIGN KEY (athlete_id) REFERENCES athletes(id)
    )""")
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(athletes)")
    columns = [row[1] for row in cur.fetchall()]
    if "goals" not in columns:
        conn.execute("ALTER TABLE athletes ADD COLUMN goals TEXT")
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
    conn.commit()
    conn.close()

def _row_to_ride(row) -> dict:
    try:
        gps = json.loads(row[10]) if row[10] else None
    except (json.JSONDecodeError, TypeError):
        gps = None
    return {"id": row[0], "athlete_id": row[1], "date": row[2], "distance_km": row[3], "duration_minutes": row[4], "avg_speed_kmh": row[5], "weight_kg": row[6], "calories": row[7], "heart_rate_avg": row[8], "elevation_gain_m": row[9], "gps_points": gps, "created_at": row[11]}

def save_ride(ride: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        cur.execute("""INSERT INTO rides (athlete_id, date, distance_km, duration_minutes, avg_speed_kmh, weight_kg, calories, heart_rate_avg, elevation_gain_m, gps_points, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ride.get("athlete_id"), ride.get("date"), ride.get("distance_km", 0), ride.get("duration_minutes", 0), ride.get("avg_speed_kmh", 0),
             ride.get("weight_kg", 70), ride.get("calories", 0), ride.get("heart_rate_avg"),
             ride.get("elevation_gain_m"), gps_points, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return cur.lastrowid

def get_ride(ride_id: int) -> Optional[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
        row = cur.fetchone()
        if row:
            return _row_to_ride(row)
        return None

def get_rides_by_athlete(athlete_id: int) -> List[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rides WHERE athlete_id = ?", (athlete_id,))
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]

def get_all_rides() -> List[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM rides")
        rows = cur.fetchall()
        return [_row_to_ride(r) for r in rows]

def delete_ride(ride_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def update_ride(ride_id: int, ride: dict) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
        cur.execute("""UPDATE rides SET athlete_id=?, date=?, distance_km=?, duration_minutes=?, avg_speed_kmh=?, weight_kg=?, calories=?, heart_rate_avg=?, elevation_gain_m=?, gps_points=? WHERE id=?""",
            (ride.get("athlete_id"), ride.get("date"), ride.get("distance_km", 0), ride.get("duration_minutes", 0),
             ride.get("avg_speed_kmh", 0), ride.get("weight_kg", 70), ride.get("calories", 0),
             ride.get("heart_rate_avg"), ride.get("elevation_gain_m"), gps_points, ride_id))
        conn.commit()
        return cur.rowcount > 0

def save_athlete(athlete: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""INSERT INTO athletes (name, age, weight_kg, height_cm, fat_percentage, years_active, weekly_sessions, monthly_hours, annual_hours, experience_level, goals, preferred_terrain, weekly_volume_km, best_segments, medical_notes, equipment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete.get("name"), athlete.get("age", 30), athlete.get("weight_kg", 70), athlete.get("height_cm"),
             athlete.get("fat_percentage"), athlete.get("years_active", 1), athlete.get("weekly_sessions", 3),
             athlete.get("monthly_hours", 0), athlete.get("annual_hours", 0), athlete.get("experience_level", "Beginner"),
             athlete.get("goals"), athlete.get("preferred_terrain"), athlete.get("weekly_volume_km", 0),
             athlete.get("best_segments"), athlete.get("medical_notes"), athlete.get("equipment"),
             datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return cur.lastrowid

def get_athlete(athlete_id: int) -> Optional[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "age": row[2], "weight_kg": row[3], "height_cm": row[4], "fat_percentage": row[5], "years_active": row[6], "weekly_sessions": row[7], "monthly_hours": row[8], "annual_hours": row[9], "experience_level": row[10], "goals": row[11], "preferred_terrain": row[12], "weekly_volume_km": row[13], "best_segments": row[14], "medical_notes": row[15], "equipment": row[16]}
        return None

def save_metric(metric: dict) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""INSERT INTO metrics (athlete_id, ride_id, fatigue_score, recovery_hours, calories_per_km, efficiency_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (metric.get("athlete_id"), metric.get("ride_id"), metric.get("fatigue_score"), metric.get("recovery_hours"),
             metric.get("calories_per_km"), metric.get("efficiency_score"), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return cur.lastrowid

def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    existing = get_athlete(athlete_id)
    if not existing: return False
    merged = {**existing, **athlete_data}
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""UPDATE athletes SET name=?, age=?, weight_kg=?, height_cm=?, fat_percentage=?, years_active=?, weekly_sessions=?, monthly_hours=?, annual_hours=?, experience_level=?, goals=?, preferred_terrain=?, weekly_volume_km=?, best_segments=?, medical_notes=?, equipment=? WHERE id=?""",
            (merged.get("name"), merged.get("age", 30), merged.get("weight_kg", 70), merged.get("height_cm"),
             merged.get("fat_percentage"), merged.get("years_active", 1), merged.get("weekly_sessions", 3),
             merged.get("monthly_hours", 0), merged.get("annual_hours", 0), merged.get("experience_level", "Beginner"),
             merged.get("goals"), merged.get("preferred_terrain"), merged.get("weekly_volume_km", 0),
             merged.get("best_segments"), merged.get("medical_notes"), merged.get("equipment"), athlete_id))
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
        conn.commit()

def backup_database(backup_path: Optional[str] = None) -> str:
    import shutil
    from pathlib import Path
    if not Path(DB_PATH).exists():
        raise FileNotFoundError(f"Database {DB_PATH} does not exist yet")
    if backup_path is None: backup_path = f"rides_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path

def save_chat_message(athlete_id: Optional[int], role: str, content: str) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""INSERT INTO chat_history (athlete_id, role, content, created_at)
            VALUES (?, ?, ?, ?)""",
            (athlete_id, role, content, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return cur.lastrowid

def get_chat_history(athlete_id: int, limit: int = 10) -> List[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT role, content, created_at FROM chat_history WHERE athlete_id = ? ORDER BY id DESC LIMIT ?", (athlete_id, limit))
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]

def clear_chat_history(athlete_id: int) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM chat_history WHERE athlete_id = ?", (athlete_id,))
        conn.commit()
        return cur.rowcount > 0

def get_all_athletes() -> List[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, experience_level FROM athletes")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "experience_level": r[2]} for r in rows]

__all__ = ["save_ride", "get_ride", "get_all_rides", "get_rides_by_athlete", "get_all_athletes", "delete_ride", "update_ride", "init_db", "save_athlete", "get_athlete", "save_metric", "update_athlete", "create_indices", "backup_database", "get_db_connection", "save_chat_message", "get_chat_history", "clear_chat_history"]
