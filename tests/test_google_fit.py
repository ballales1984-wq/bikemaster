"""Test coverage for Google Fit integration."""

from bike_analyzer.backend.ingestion.google_fit import (
    _ms_to_iso,
    get_authorization_url,
    google_fit_to_ride,
)


def test_get_authorization_url():
    url = get_authorization_url("my_client_id", "http://localhost:8000/callback", "random_state")
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=my_client_id" in url
    assert "response_type=code" in url
    assert "scope=" in url
    assert "state=random_state" in url


def test_get_authorization_url_default_redirect():
    url = get_authorization_url("my_client_id")
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback" in url


def test_ms_to_iso_valid():
    # 2024-06-18T05:02:42+00:00
    assert _ms_to_iso("1718686962000").startswith("2024-06-18")


def test_ms_to_iso_empty():
    assert _ms_to_iso("") == ""


def test_google_fit_to_ride_empty():
    assert google_fit_to_ride([]) == []


def test_google_fit_to_ride_cycling_activity():
    """Tests the Sessions API format (startTimeMillis/endTimeMillis)."""
    now_ms = 1718686962000
    one_hour_later = now_ms + 3600000
    activities = [
        {
            "id": "session-123",
            "startTimeMillis": str(now_ms),
            "endTimeMillis": str(one_hour_later),
            "activity": 1,
            "name": "Morning Ride",
        }
    ]
    rides = google_fit_to_ride(activities)
    assert len(rides) == 1
    assert rides[0]["date"] == "2024-06-18"
    assert rides[0]["duration_minutes"] == 60.0
    assert rides[0]["title"] == "Morning Ride"
    assert rides[0]["external_source"] == "google_fit"
    assert rides[0]["external_id"] == "session-123"
    assert rides[0]["avg_speed_kmh"] == 0


def test_google_fit_to_ride_skips_non_cycling():
    activities = [
        {
            "id": "run-1",
            "startTimeMillis": "1718686962000",
            "endTimeMillis": "1718690562000",
            "activity": 7,
            "name": "Running",
        }
    ]
    assert google_fit_to_ride(activities) == []
