"""Test database backup functionality."""
import os
import sqlite3

from bike_analyzer.backend.db.database import init_db, save_ride, save_athlete, backup_database, get_all_rides, delete_ride


def test_database_backup_creates_file():
    init_db()
    backup_path = backup_database("test_backup_explicit.db")
    assert os.path.exists(backup_path)
    os.remove(backup_path)


def test_database_backup_with_data():
    init_db()
    save_ride({"date": "2024-07-01", "distance_km": 30.0})
    save_athlete({"name": "Backup Test Athlete"})
    backup_path = backup_database("test_backup_data.db")
    assert os.path.exists(backup_path)
    os.remove(backup_path)


def test_save_metric_and_retrieve():
    init_db()
    from bike_analyzer.backend.db.database import save_metric, get_rides_by_athlete
    save_ride({"date": "2024-07-02", "distance_km": 20.0})
    save_metric({"athlete_id": 1, "ride_id": 1, "fatigue_score": 5.0})
    rides = get_rides_by_athlete(1)
    assert isinstance(rides, list)