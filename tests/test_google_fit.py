"""Test coverage for Google Fit integration."""

from bike_analyzer.backend.ingestion.google_fit import (
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


def test_google_fit_to_ride_empty():
    rides = google_fit_to_ride([])
    assert rides == []


def test_google_fit_to_ride_cycling_activity():
    activities = [
        {
            "startTime": "2024-06-01T08:00:00Z",
            "endTime": "2024-06-01T09:00:00Z",
            "dataType": "cycling",
            "value": [
                {"intVal": 3600000, "format": "duration"},
                {"intVal": 20000, "format": "distance"},
            ],
        }
    ]
    rides = google_fit_to_ride(activities)
    assert len(rides) == 1
    assert rides[0]["distance_km"] == 20.0


def test_google_fit_to_ride_non_cycling():
    activities = [{"startTime": "2024-06-01T08:00:00Z", "dataType": "running", "value": []}]
    rides = google_fit_to_ride(activities)
    assert rides == []
