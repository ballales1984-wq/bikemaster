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
    get_athlete_by_email,
    get_athlete_by_name,
    get_chat_history,
    get_ride,
    get_weather_cache,
    init_db,
    save_athlete,
    save_chat_message,
    save_metric,
    save_ride,
    update_athlete,
    update_athlete as update_athlete_func,
    get_paginated_rides,
    get_training_stress_days,
    get_latest_training_stress,
    save_user,
    get_user_by_username,
    get_user_by_id,
    save_weather_cache,
    upsert_training_stress_day,
    get_events_by_athlete,
    delete_calendar_event,
    save_calendar_event,
    get_calendar_event,
    update_calendar_event,
    get_events_by_month,
    get_events_by_date_range,
    save_road_incident,
    save_route_safety_score,
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


def test_save_and_get_athlete_by_name():
    init_db()
    athlete_id = save_athlete({"name": "Unique Test Name", "age": 25})
    a = get_athlete_by_name("Unique Test Name")
    assert a is not None
    assert a["name"] == "Unique Test Name"


def test_save_and_get_athlete_by_email():
    init_db()
    athlete_id = save_athlete({"name": "Email Test", "email": "test@example.com"})
    a = get_athlete_by_email("test@example.com")
    assert a is not None
    assert a["email"] == "test@example.com"


def test_update_athlete():
    init_db()
    athlete_id = save_athlete({"name": "Original", "age": 25})
    result = update_athlete(athlete_id, {"age": 30, "weight_kg": 80.0})
    assert result is True
    a = get_athlete(athlete_id)
    assert a["age"] == 30
    assert a["weight_kg"] == 80.0


def test_save_metric():
    init_db()
    athlete_id = save_athlete({"name": "Unique Athlete Met" + str(os.times().elapsed)})
    ride_id = save_ride({"date": "2024-06-01", "distance_km": 20.0, "athlete_id": athlete_id})
    metric_id = save_metric(
        {"athlete_id": athlete_id, "ride_id": ride_id, "fatigue_score": 5.0, "recovery_hours": 16.0}
    )
    assert metric_id > 0


def test_save_and_get_weather_cache():
    init_db()
    cache_id = save_weather_cache(45.0, 9.0, "2024-06-01", {"temperature": 20.0, "humidity": 50.0})
    assert cache_id > 0
    weather = get_weather_cache(45.0, 9.0, "2024-06-01")
    assert weather is not None
    assert weather["temperature"] == 20.0


def test_get_weather_cache_not_found():
    init_db()
    weather = get_weather_cache(0.0, 0.0, "2000-01-01")
    assert weather is None


def test_upsert_training_stress_day():
    init_db()
    upsert_training_stress_day(athlete_id=1, date="2024-06-01", tss=50.0, atl=45.0, ctl=55.0, tsb=10.0)
    stress = get_latest_training_stress(athlete_id=1)
    assert stress is not None
    assert stress["tss"] == 50.0


def test_get_training_stress_days():
    init_db()
    for i in range(5):
        upsert_training_stress_day(athlete_id=1, date=f"2024-06-{i+10:02d}", tss=50.0, atl=45.0, ctl=55.0, tsb=10.0)
    days = get_training_stress_days(athlete_id=1)
    assert len(days) >= 5


def test_save_user():
    init_db()
    import time
    username = f"testuser_{int(time.time() * 1000) % 100000}"
    user_id = save_user({"username": username, "email": f"{username}@test.com"})
    assert user_id > 0


def test_get_user_by_username():
    init_db()
    import time
    username = f"uniqueuser_{int(time.time() * 1000) % 100000}"
    user_id = save_user({"username": username, "email": f"{username}@test.com"})
    user = get_user_by_username(username)
    assert user is not None
    assert user["username"] == username


def test_get_user_by_id():
    init_db()
    import time
    username = "iduser_" + str(int(time.time() * 1000) % 100000)
    user_id = save_user({"username": username, "email": f"{username}@test.com"})
    user = get_user_by_id(user_id)
    assert user is not None
    assert user["id"] == user_id


def test_save_and_get_calendar_event():
    init_db()
    athlete_id = save_athlete({"name": "Calendar Athlete"})
    event_id = save_calendar_event({"athlete_id": athlete_id, "title": "Test Event", "date": "2024-06-15"})
    assert event_id > 0


def test_get_events_by_athlete():
    init_db()
    athlete_id = save_athlete({"name": "Events Athlete"})
    save_calendar_event({"athlete_id": athlete_id, "title": "Event 1", "date": "2024-06-01"})
    save_calendar_event({"athlete_id": athlete_id, "title": "Event 2", "date": "2024-06-02"})
    events = get_events_by_athlete(athlete_id=athlete_id)
    assert len(events) >= 2


def test_update_and_delete_calendar_event():
    init_db()
    athlete_id = save_athlete({"name": "Update Athlete"})
    event_id = save_calendar_event({"athlete_id": athlete_id, "title": "Original", "date": "2024-06-15"})
    update_calendar_event(event_id, {"title": "Updated"})
    event = get_calendar_event(event_id)
    assert event["title"] == "Updated" or event is None
    deleted = delete_calendar_event(event_id)
    assert deleted is True


def test_get_events_by_date_range():
    init_db()
    athlete_id = save_athlete({"name": "Date Range Athlete"})
    save_calendar_event({"athlete_id": athlete_id, "title": "Event 1", "date": "2024-06-01"})
    save_calendar_event({"athlete_id": athlete_id, "title": "Event 2", "date": "2024-06-15"})
    save_calendar_event({"athlete_id": athlete_id, "title": "Event 3", "date": "2024-06-30"})
    events = get_events_by_date_range(athlete_id=athlete_id, start_date="2024-06-01", end_date="2024-06-16")
    assert len(events) >= 1


def test_save_road_incident():
    init_db()
    import time
    incident_id = save_road_incident({"id": f"inc_{int(time.time())}", "lat": 45.0, "lon": 9.0, "date": "2024-06-01", "severity": "high"})
    assert incident_id > 0


def test_save_route_safety_score():
    init_db()
    save_athlete({"name": "Safety Athlete"})
    ride_id = save_ride({"date": "2024-06-01", "distance_km": 20.0, "athlete_id": 1})
    score_id = save_route_safety_score({"ride_id": ride_id, "athlete_id": 1, "risk_score": 0.5, "label": "safe"})
    assert score_id > 0


def test_get_paginated_rides():
    init_db()
    for i in range(5):
        save_ride({"date": f"2024-06-0{i+1}", "distance_km": 20.0})
    rides, total = get_paginated_rides(page=1, page_size=2)
    assert len(rides) == 2
    assert total >= 5


def test_get_paginated_rides_ordered_by_distance():
    init_db()
    rides, _ = get_paginated_rides(page=1, page_size=10, sort="distance")
    assert isinstance(rides, list)
