"""Test database simple layer."""

import os
import sqlite3

import pytest

from bike_analyzer.backend.db.database import (
    DB_PATH,
    backup_database,
    clear_chat_history,
    create_indices,
    delete_ride,
    get_all_athletes,
    get_all_rides,
    get_athlete,
    get_chat_history,
    get_ride,
    init_db,
    save_athlete,
    save_chat_message,
    save_ride,
    update_athlete,
)


def test_save_and_get_ride():
    init_db()
    ride_id = save_ride(
        {
            "date": "2024-06-15",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0,
            "weight_kg": 70.0,
            "calories": 500,
            "heart_rate_avg": 150,
            "elevation_gain_m": 100,
        }
    )
    r = get_ride(ride_id)
    assert r is not None
    assert r["date"] == "2024-06-15"
    assert r["distance_km"] == 25.0


def test_save_ride_reuses_existing_external_identity():
    init_db()
    ride = {
        "athlete_id": 1,
        "date": "2026-06-14",
        "distance_km": 25.0,
        "duration_minutes": 60.0,
        "avg_speed_kmh": 25.0,
        "weight_kg": 70.0,
        "external_source": "strava",
        "external_id": "12345",
        "title": "Morning Ride",
    }

    first_id = save_ride(ride)
    second_id = save_ride(ride)

    assert second_id == first_id
    matching_rides = [
        r
        for r in get_all_rides()
        if r["external_source"] == "strava" and r["external_id"] == "12345"
    ]
    assert len(matching_rides) == 1


def test_get_all_rides():
    init_db()
    save_ride({"date": "2024-06-16"})
    rides = get_all_rides()
    assert len(rides) >= 1


def test_delete_ride():
    init_db()
    ride_id = save_ride({"date": "2024-06-17"})
    deleted = delete_ride(ride_id)
    assert deleted
    assert get_ride(ride_id) is None


def test_save_and_get_athlete():
    init_db()
    athlete_id = save_athlete(
        {"name": "Test Athlete", "age": 30, "weight_kg": 75.0, "experience_level": "Intermediate"}
    )
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


def test_get_ride_not_found():
    init_db()
    r = get_ride(99999)
    assert r is None


def test_delete_ride_not_found():
    init_db()
    deleted = delete_ride(99999)
    assert deleted is False


def test_get_athlete_not_found():
    init_db()
    a = get_athlete(99999)
    assert a is None


def test_update_athlete_not_found():
    init_db()
    result = update_athlete(99999, {"name": "Nuovo"})
    assert result is False


def test_backup_missing_db(tmp_path):
    import bike_analyzer.backend.db.database as db_mod

    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = str(tmp_path / "nonexistent.db")
    with pytest.raises(FileNotFoundError):
        backup_database()
    db_mod.DB_PATH = original_path


def test_save_chat_and_history():
    init_db()
    msg_id = save_chat_message(athlete_id=1, role="user", content="Ciao AI Coach")
    assert msg_id > 0
    history = get_chat_history(athlete_id=1, limit=5)
    assert len(history) >= 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Ciao AI Coach"


def test_clear_chat_history():
    init_db()
    save_chat_message(athlete_id=1, role="user", content="test")
    cleared = clear_chat_history(athlete_id=1)
    assert cleared is True
    history = get_chat_history(athlete_id=1)
    assert len(history) == 0


def test_get_all_athletes():
    init_db()
    save_athlete({"name": "Athlete1", "experience_level": "Beginner"})
    save_athlete({"name": "Athlete2", "experience_level": "Advanced"})
    athletes = get_all_athletes()
    names = [a["name"] for a in athletes]
    assert "Athlete1" in names
    assert "Athlete2" in names
