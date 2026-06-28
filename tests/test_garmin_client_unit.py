"""Tests for Garmin client unit-level coverage."""

from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.ingestion.garmin_client import (
    exchange_code_for_token,
    fetch_activities,
    garmin_to_ride,
    get_authorization_url,
)


class TestGarminOAuth:
    def test_get_authorization_url_returns_dict(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_KEY", "test_key"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_REDIRECT_URI", "https://test"),
        ):
            result = get_authorization_url()
            assert "auth_url" in result
            assert "state" in result
            assert "garmin.com" in result["auth_url"]

    def test_get_authorization_url_with_state(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_KEY", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_REDIRECT_URI", "https://test"),
        ):
            result = get_authorization_url(state="custom_state")
            assert result["state"] == "custom_state"

    def test_get_authorization_url_missing_key(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_KEY", ""),
            pytest.raises(RuntimeError, match="GARMIN_CONSUMER_KEY"),
        ):
            get_authorization_url()

    @patch("bike_analyzer.backend.ingestion.garmin_client.requests.post")
    def test_exchange_code_for_token(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "garmin_access",
            "refresh_token": "garmin_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_resp

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_KEY", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_SECRET", "secret"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_TOKEN_URL", "https://test"),
        ):
            result = exchange_code_for_token("auth_code")
            assert result["access_token"] == "garmin_access"

    @patch("bike_analyzer.backend.ingestion.garmin_client.requests.post")
    def test_exchange_code_raises_on_error(self, mock_post):
        from requests.exceptions import HTTPError

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_post.return_value = mock_resp

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_KEY", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_CONSUMER_SECRET", "secret"),
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_TOKEN_URL", "https://test"),
            pytest.raises(HTTPError),
        ):
            exchange_code_for_token("bad_code")


class TestGarminActivities:
    @patch("bike_analyzer.backend.ingestion.garmin_client.requests.get")
    def test_fetch_activities(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"activityId": 1, "activityName": "Morning Ride", "startTimeGMT": "2024-06-15T08:00:00.000Z"},
        ]
        mock_get.return_value = mock_resp

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client.GARMIN_API_BASE_URL", "https://test"),
            patch("bike_analyzer.backend.ingestion.garmin_client.store_token"),
        ):
            activities = fetch_activities("access_token_123")
            assert len(activities) == 1

    def test_garmin_to_ride(self):
        activity = {
            "activityId": 1,
            "activityName": "Test Ride",
            "startTimeLocal": "2024-06-15T08:00:00.000Z",
            "distance": 25000,
            "duration": 3600,
            "elevationGain": 200,
            "averageHR": 145,
            "activityType": {"typeKey": "cycling"},
        }
        ride = garmin_to_ride(activity)
        assert ride["date"] == "2024-06-15"
        assert ride["distance_km"] == 25.0
        assert ride["duration_minutes"] == 60.0
