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
    conn.commit()
    conn.close()

def save_ride(ride: dict) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    gps_points = json.dumps(ride.get("gps_points")) if ride.get("gps_points") else None
    cur.execute("""INSERT INTO rides (date, distance_km, duration_minutes, avg_speed_kmh, weight_kg, calories, heart_rate_avg, elevation_gain_m, gps_points, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ride.get("date"), ride.get("distance_km", 0), ride.get("duration_minutes", 0), ride.get("avg_speed_kmh", 0),
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
        return {"id": row[0], "date": row[1], "distance_km": row[2], "duration_minutes": row[3], "avg_speed_kmh": row[4], "weight_kg": row[5], "calories": row[6], "heart_rate_avg": row[7], "elevation_gain_m": row[8], "gps_points": json.loads(row[9]) if row[9] else None, "created_at": row[10]}
    return None

def get_all_rides() -> List[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM rides")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "distance_km": r[2], "duration_minutes": r[3], "avg_speed_kmh": r[4], "weight_kg": r[5], "calories": r[6], "heart_rate_avg": r[7], "elevation_gain_m": r[8], "gps_points": json.loads(r[9]) if r[9] else None, "created_at": r[10]} for r in rows]

def delete_ride(ride_id: int) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM rides WHERE id = ?", (ride_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

__all__ = ["save_ride", "get_ride", "get_all_rides", "delete_ride", "init_db"]