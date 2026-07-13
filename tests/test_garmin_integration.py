"""Tests for Garmin integration."""

from bike_analyzer.backend.ingestion.garmin_client import garmin_to_ride


def test_garmin_to_ride_cycling():
    act = {
        "activityId": 98765,
        "activityName": "Weekend Gran Fondo",
        "activityType": {"typeKey": "road_biking"},
        "startTimeLocal": "2026-06-14T07:30:00",
        "duration": 5400.0,
        "distance": 65000.0,
        "averageSpeed": 11.5,
        "elevationGain": 1800,
        "averageHR": 152,
        "calories": 1200,
    }
    ride = garmin_to_ride(act, weight_kg=75.0)
    assert "error" not in ride or not ride.get("error")
    assert ride["distance_km"] == 65.0
    assert ride["duration_minutes"] == 90.0
    assert ride["elevation_gain_m"] == 1800
    assert ride["heart_rate_avg"] == 152
    assert ride["external_source"] == "garmin"
    assert ride["external_id"] == "98765"
    assert ride["title"] == "Weekend Gran Fondo"


def test_garmin_to_ride_skips_non_cycling():
    act = {
        "activityType": {"typeKey": "running"},
        "startTimeLocal": "2026-06-14T07:30:00",
        "duration": 1800.0,
        "distance": 5000.0,
    }
    ride = garmin_to_ride(act)
    assert ride.get("skipped") is True


def test_garmin_to_ride_string_activity_type():
    act = {
        "activityType": "cycling",
        "startTimeLocal": "2026-06-14T07:30:00",
        "duration": 3600.0,
        "distance": 30000.0,
    }
    ride = garmin_to_ride(act)
    assert "error" not in ride or not ride.get("error")


def test_garmin_to_ride_zero_values():
    act = {
        "activityType": {"typeKey": "mountain_biking"},
        "startTimeLocal": "",
        "duration": 0,
        "distance": 0,
    }
    ride = garmin_to_ride(act)
    assert ride["date"] == ""
    assert ride["duration_minutes"] == 0
    assert ride["avg_speed_kmh"] == 0


def test_garmin_sync_endpoint_is_idempotent(client, monkeypatch):
    import bike_analyzer.backend.ingestion.garmin_client as gc

    activity = {
        "activityId": 98765,
        "activityName": "Weekend Gran Fondo",
        "activityType": {"typeKey": "road_biking"},
        "startTimeLocal": "2026-06-14T07:30:00",
        "duration": 5400.0,
        "distance": 65000.0,
        "averageSpeed": 11.5,
        "elevationGain": 1800,
        "averageHR": 152,
        "calories": 1200,
    }
    async def _valid_token(athlete_id):
        return "token"

    async def _fetch(token):
        return [activity, activity]

    monkeypatch.setattr(gc, "get_valid_token", _valid_token)
    monkeypatch.setattr(gc, "fetch_activities", _fetch)

    response = client.post("/api/v1/import/garmin/sync?background=false")

    assert response.status_code == 200
    data = response.json()
    assert data["total_fetched"] == 2
    assert data["imported"] == 1
    assert len(data["rides"]) == 1
    rides = client.get("/api/v1/rides").json()["rides"]
    assert len(rides) == 1
    assert rides[0]["external_source"] == "garmin"
    assert rides[0]["external_id"] == "98765"
