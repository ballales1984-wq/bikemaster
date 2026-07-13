"""Tests for google_fit module."""

import time
from unittest.mock import patch

import pytest

from bike_analyzer.backend.ingestion.google_fit import (
    _ms_to_iso,
    fetch_cycling_activities,
    get_authorization_url,
    google_fit_to_ride,
)


class TestMsToIso:
    def test_none(self):
        assert _ms_to_iso(None) == ""

    def test_empty_string(self):
        assert _ms_to_iso("") == ""

    def test_zero(self):
        result = _ms_to_iso("0")
        assert "1970" in result

    def test_valid_millis(self):
        ms = "1719560000000"
        result = _ms_to_iso(ms)
        assert "2024" in result
        assert "+00:00" in result

    def test_integer_input(self):
        ms = 1719560000000
        result = _ms_to_iso(ms)
        assert "2024" in result

    def test_invalid_string(self):
        result = _ms_to_iso("not_a_number")
        assert result == "not_a_number"

    def test_recent_timestamp(self):
        ms = int(time.time() * 1000)
        result = _ms_to_iso(ms)
        from datetime import datetime

        dt = datetime.fromisoformat(result)
        assert dt.year >= 2024


class TestGetAuthorizationUrl:
    def test_basic_url(self):
        url = get_authorization_url("client_id")
        assert "accounts.google.com" in url
        assert "client_id=client_id" in url

    def test_custom_redirect_uri(self):
        url = get_authorization_url("client_id", redirect_uri="https://example.com/callback")
        assert "redirect_uri=" in url

    def test_custom_state(self):
        url = get_authorization_url("client_id", state="csrf")
        assert "state=csrf" in url

    def test_response_type_code(self):
        url = get_authorization_url("client_id")
        assert "response_type=code" in url


class TestGoogleFitToRide:
    def test_cycling_activity(self):
        from datetime import UTC, datetime

        now_ms = int(datetime(2024, 6, 15, 8, 0, tzinfo=UTC).timestamp() * 1000)
        later_ms = int(datetime(2024, 6, 15, 10, 0, tzinfo=UTC).timestamp() * 1000)
        activities = [
            {"activity": 1, "startTimeMillis": str(now_ms), "endTimeMillis": str(later_ms), "name": "Morning Ride"}
        ]
        rides = google_fit_to_ride(activities)
        assert len(rides) == 1
        assert rides[0]["date"] == "2024-06-15"
        assert rides[0]["duration_minutes"] == 120.0

    def test_non_cycling_filtered(self):
        from datetime import UTC, datetime

        now_ms = int(datetime(2024, 6, 15, 8, 0, tzinfo=UTC).timestamp() * 1000)
        later_ms = int(datetime(2024, 6, 15, 9, 0, tzinfo=UTC).timestamp() * 1000)
        activities = [{"activity": 2, "startTimeMillis": str(now_ms), "endTimeMillis": str(later_ms)}]
        rides = google_fit_to_ride(activities)
        assert rides == []

    def test_cycling_by_name(self):
        from datetime import UTC, datetime

        now_ms = int(datetime(2024, 6, 15, 8, 0, tzinfo=UTC).timestamp() * 1000)
        later_ms = int(datetime(2024, 6, 15, 9, 0, tzinfo=UTC).timestamp() * 1000)
        activities = [
            {"activity": 0, "startTimeMillis": str(now_ms), "endTimeMillis": str(later_ms), "name": "Road cycling"}
        ]
        rides = google_fit_to_ride(activities)
        assert len(rides) == 1

    def test_empty_input(self):
        assert google_fit_to_ride([]) == []

    def test_distance_from_legacy_format(self):
        from datetime import UTC, datetime

        now_ms = int(datetime(2024, 6, 15, 8, 0, tzinfo=UTC).timestamp() * 1000)
        later_ms = int(datetime(2024, 6, 15, 9, 0, tzinfo=UTC).timestamp() * 1000)
        activities = [
            {
                "activity": 1,
                "startTimeMillis": str(now_ms),
                "endTimeMillis": str(later_ms),
                "value": [{"name": "distance.sum", "fpVal": 25000.0}],
            }
        ]
        rides = google_fit_to_ride(activities)
        assert rides[0]["distance_km"] == 25.0

    def test_avg_speed_calculation(self):
        from datetime import UTC, datetime

        now_ms = int(datetime(2024, 6, 15, 8, 0, tzinfo=UTC).timestamp() * 1000)
        later_ms = int(datetime(2024, 6, 15, 9, 0, tzinfo=UTC).timestamp() * 1000)
        activities = [
            {
                "activity": 1,
                "startTimeMillis": str(now_ms),
                "endTimeMillis": str(later_ms),
                "value": [{"name": "distance.sum", "fpVal": 30000.0}],
            }
        ]
        rides = google_fit_to_ride(activities)
        assert rides[0]["avg_speed_kmh"] == 30.0

    @patch("bike_analyzer.backend.ingestion.google_fit.request_json")
    async def test_fetch_cycling_activities_success(self, mock_get):
        mock_get.return_value = {"session": [{"activity": 1}]}
        result = await fetch_cycling_activities("token")
        assert isinstance(result, list)

    @patch("bike_analyzer.backend.ingestion.google_fit.request_json")
    async def test_fetch_cycling_activities_raises_on_failure(self, mock_get):
        import httpx

        mock_get.side_effect = httpx.HTTPStatusError(
            "403 Client Error",
            request=httpx.Request("GET", "https://www.googleapis.com"),
            response=httpx.Response(403),
        )
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_cycling_activities("token")
