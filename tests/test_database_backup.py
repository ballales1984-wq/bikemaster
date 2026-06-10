"""Test database backup functionality."""

import os

from bike_analyzer.backend.db.database import (
    backup_database,
    clear_chat_history,
    get_athlete,
    get_chat_history,
    init_db,
    save_athlete,
    save_chat_message,
    save_ride,
    update_athlete,
)


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
    from bike_analyzer.backend.db.database import get_rides_by_athlete, save_metric

    save_ride({"date": "2024-07-02", "distance_km": 20.0})
    save_metric({"athlete_id": 1, "ride_id": 1, "fatigue_score": 5.0})
    rides = get_rides_by_athlete(1)
    assert isinstance(rides, list)


def test_save_chat_message():
    init_db()
    msg_id = save_chat_message(1, "user", "Ciao coach")
    assert msg_id > 0


def test_get_chat_history():
    init_db()
    save_chat_message(1, "user", "Domanda")
    save_chat_message(1, "assistant", "Risposta")
    history = get_chat_history(1)
    assert len(history) >= 2
    assert history[0]["role"] == "assistant"


def test_clear_chat_history():
    init_db()
    save_chat_message(1, "user", "Test")
    cleared = clear_chat_history(1)
    assert cleared is True


def test_update_athlete_partial():
    init_db()
    athlete_id = save_athlete(
        {"name": "Originale", "age": 30, "weight_kg": 70.0, "experience_level": "Beginner"}
    )
    updated = update_athlete(athlete_id, {"goals": "Gran Fondo"})
    assert updated is True
    a = get_athlete(athlete_id)
    assert a["goals"] == "Gran Fondo"
    assert a["name"] == "Originale"
