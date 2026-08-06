"""Tests for Strava client unit-level coverage."""

import time
from unittest.mock import patch

import httpx
import pytest

from bike_analyzer.backend.ingestion.strava_client import (
    build_authorization_url,
    exchange_code_for_token,
    fetch_activities,
    generate_code_challenge,
    generate_code_verifier,
    get_authorization_url,
    refresh_access_token,
    strava_to_ride,
)


class TestStravaPKCE:
    def test_generate_code_verifier(self):
        v = generate_code_verifier()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_generate_code_challenge(self):
        verifier = "test_verifier_123"
        challenge = generate_code_challenge(verifier)
        assert isinstance(challenge, str)
        assert "=" not in challenge

    def test_code_challenge_deterministic(self):
        verifier = "consistent_test_verifier"
        c1 = generate_code_challenge(verifier)
        c2 = generate_code_challenge(verifier)
        assert c1 == c2

    def test_build_authorization_url(self):
        url = build_authorization_url("state123", "challenge123")
        assert "strava.com" in url
        assert "state123" in url
        assert "code_challenge=challenge123" in url

    @patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", "test_client")
    def test_get_authorization_url_returns_dict(self):
        result = get_authorization_url()
        assert "auth_url" in result
        assert "state" in result
        assert "code_verifier" in result
        assert "strava.com" in result["auth_url"]

    def test_get_authorization_url_with_state(self):
        with patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", "test"):
            result = get_authorization_url(state="custom_state")
            assert result["state"] == "custom_state"

    def test_get_authorization_url_missing_client_id(self):
        with (
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", ""),
            pytest.raises(RuntimeError, match="STRAVA_CLIENT_ID"),
        ):
            get_authorization_url()


class TestStravaTokenExchange:
    @patch("bike_analyzer.backend.ingestion.strava_client.request_json")
    async def test_exchange_code_for_token(self, mock_post):
        mock_post.return_value = {
            "access_token": "strava_access",
            "refresh_token": "strava_refresh",
            "expires_at": int(time.time()) + 3600,
        }

        with (
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", "test"),
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_secret", "secret"),
            patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_TOKEN_URL", "https://test"),
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_redirect_uri", "https://test"),
        ):
            result = await exchange_code_for_token("auth_code", "verifier123")
            assert result["access_token"] == "strava_access"

    @patch("bike_analyzer.backend.ingestion.strava_client.request_json")
    async def test_exchange_code_raises_on_error(self, mock_post):
        mock_post.side_effect = httpx.HTTPStatusError(
            "400 Bad Request",
            request=httpx.Request("POST", "https://test"),
            response=httpx.Response(400),
        )

        with (
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", "test"),
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_secret", "secret"),
            patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_TOKEN_URL", "https://test"),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await exchange_code_for_token("bad_code", "bad_verifier")


class TestStravaTokenRefresh:
    @patch("bike_analyzer.backend.ingestion.strava_client.request_json")
    async def test_refresh_access_token(self, mock_post):
        mock_post.return_value = {"access_token": "new_token", "expires_at": int(time.time()) + 3600}

        with (
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_id", "test"),
            patch("bike_analyzer.backend.ingestion.strava_client._s.strava_client_secret", "secret"),
            patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_TOKEN_URL", "https://test"),
        ):
            result = await refresh_access_token("refresh_token")
            assert result["access_token"] == "new_token"


class TestStravaActivities:
    @patch("bike_analyzer.backend.ingestion.strava_client.request_json")
    async def test_fetch_activities(self, mock_get):
        mock_get.return_value = [
            {
                "id": 1,
                "name": "Morning Ride",
                "type": "Ride",
                "start_date": "2024-06-15T08:00:00Z",
                "distance": 25000,
                "moving_time": 3600,
            },
        ]

        with patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_API_BASE_URL", "https://test"):
            activities = await fetch_activities("access_token")
            assert len(activities) == 1
            assert activities[0]["name"] == "Morning Ride"

    def test_strava_to_ride(self):
        activity = {
            "id": 1,
            "name": "Test Ride",
            "type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 25000,
            "moving_time": 3600,
            "total_elevation_gain": 200,
            "average_heartrate": 145,
            "average_speed": 10.0,
        }
        ride = strava_to_ride(activity)
        assert ride["date"] == "2024-06-15"
        assert ride["distance_km"] == 25.0
        assert ride["duration_minutes"] == 60.0
