"""Test database simple layer."""
import os
from bike_analyzer.backend.db.database import save_ride, get_ride, get_all_rides, delete_ride, init_db, save_athlete, get_athlete, create_indices, backup_database, DB_PATH
import sqlite3

def test_save_and_get_ride():
    init_db()
    ride_id = save_ride({"date": "2024-06-15", "distance_km": 25.0, "duration_minutes": 60.0, "avg_speed_kmh": 25.0, "weight_kg": 70.0, "calories": 500, "heart_rate_avg": 150, "elevation_gain_m": 100})
    r = get_ride(ride_id)
    assert r is not None
    assert r["date"] == "2024-06-15"
    assert r["distance_km"] == 25.0

def test_get_all_rides():
    init_db()
    save_ride({"date": "2024-06-16"})
    rides = get_all_rides()
    assert len(rides) >= 1

def test_delete_ride():
    init_db()
    ride_id = save_ride({"date": "2024-06-17"})
    deleted = delete_ride(ride_id)
    assert deleted == True
    assert get_ride(ride_id) is None

def test_save_and_get_athlete():
    init_db()
    athlete_id = save_athlete({"name": "Test Athlete", "age": 30, "weight_kg": 75.0, "experience_level": "Intermediate"})
    a = get_athlete(athlete_id)
    assert a is not None
    assert a["name"] == "Test Athlete"
    assert a["experience_level"] == "Intermediate"

def test_create_indices():
    init_db()
    create_indices()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rides_date'")
    assert cur.fetchone() is not None
    conn.close()

def test_backup_database():
    init_db()
    backup_path = backup_database("test_backup.db")
    assert os.path.exists(backup_path)
    os.remove(backup_path)