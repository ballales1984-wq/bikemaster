"""SQLite database layer (simple)."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timezone
import sqlite3
import json

DB_PATH = "rides.db"

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
        created_at TEXT
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
    conn.commit()
    conn.close()

def save_ride(ride: dict) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
    cur.execute("""INSERT INTO rides (athlete_id, date, distance_km, duration_minutes, avg_speed_kmh, weight_kg, calories, heart_rate_avg, elevation_gain_m, gps_points, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ride.get("athlete_id"), ride.get("date"), ride.get("distance_km", 0), ride.get("duration_minutes", 0), ride.get("avg_speed_kmh", 0),
         ride.get("weight_kg", 70), ride.get("calories", 0), ride.get("heart_rate_avg"),
         ride.get("elevation_gain_m"), gps_points, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    ride_id = cur.lastrowid
    conn.close()
    return ride_id

def get_ride(ride_id: int) -> Optional[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM rides WHERE id = ?", (ride_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "athlete_id": row[1], "date": row[2], "distance_km": row[3], "duration_minutes": row[4], "avg_speed_kmh": row[5], "weight_kg": row[6], "calories": row[7], "heart_rate_avg": row[8], "elevation_gain_m": row[9], "gps_points": json.loads(row[10]) if row[10] else None, "created_at": row[11]}
    return None

def get_all_rides() -> List[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM rides")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "athlete_id": r[1], "date": r[2], "distance_km": r[3], "duration_minutes": r[4], "avg_speed_kmh": r[5], "weight_kg": r[6], "calories": r[7], "heart_rate_avg": r[8], "elevation_gain_m": r[9], "gps_points": json.loads(r[10]) if r[10] else None, "created_at": r[11]} for r in rows]

def delete_ride(ride_id: int) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def save_athlete(athlete: dict) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""INSERT INTO athletes (name, age, weight_kg, height_cm, fat_percentage, years_active, weekly_sessions, monthly_hours, annual_hours, experience_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (athlete.get("name"), athlete.get("age", 30), athlete.get("weight_kg", 70), athlete.get("height_cm"),
         athlete.get("fat_percentage"), athlete.get("years_active", 1), athlete.get("weekly_sessions", 3),
         athlete.get("monthly_hours", 0), athlete.get("annual_hours", 0), athlete.get("experience_level", "Beginner"),
         datetime.now(timezone.utc).isoformat()))
    conn.commit()
    athlete_id = cur.lastrowid
    conn.close()
    return athlete_id

def get_athlete(athlete_id: int) -> Optional[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "age": row[2], "weight_kg": row[3], "height_cm": row[4], "fat_percentage": row[5], "years_active": row[6], "weekly_sessions": row[7], "monthly_hours": row[8], "annual_hours": row[9], "experience_level": row[10]}
    return None

def save_metric(metric: dict) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""INSERT INTO metrics (athlete_id, ride_id, fatigue_score, recovery_hours, calories_per_km, efficiency_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (metric.get("athlete_id"), metric.get("ride_id"), metric.get("fatigue_score"), metric.get("recovery_hours"),
         metric.get("calories_per_km"), metric.get("efficiency_score"), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    metric_id = cur.lastrowid
    conn.close()
    return metric_id

def update_athlete(athlete_id: int, athlete_data: dict) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""UPDATE athletes SET name=?, age=?, weight_kg=?, height_cm=?, fat_percentage=?, years_active=?, weekly_sessions=?, monthly_hours=?, annual_hours=?, experience_level=? WHERE id=?""",
        (athlete_data.get("name"), athlete_data.get("age", 30), athlete_data.get("weight_kg", 70), athlete_data.get("height_cm"),
         athlete_data.get("fat_percentage"), athlete_data.get("years_active", 1), athlete_data.get("weekly_sessions", 3),
         athlete_data.get("monthly_hours", 0), athlete_data.get("annual_hours", 0), athlete_data.get("experience_level", "Beginner"), athlete_id))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated

def create_indices():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_date ON rides(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rides_athlete ON rides(athlete_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_ride ON metrics(ride_id)")
    conn.commit()
    conn.close()

def backup_database(backup_path: Optional[str] = None) -> str:
    import shutil
    if backup_path is None: backup_path = f"rides_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
    init_db()
    shutil.copy2(DB_PATH, backup_path)
    return backup_path

__all__ = ["save_ride", "get_ride", "get_all_rides", "delete_ride", "init_db", "save_athlete", "get_athlete", "save_metric", "update_athlete", "create_indices", "backup_database"]