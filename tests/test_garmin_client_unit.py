"""Tests for Garmin client unit-level coverage."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bike_analyzer.backend.ingestion.garmin_client import (
    _ensure_garmin_table,
    exchange_code_for_token,
    fetch_activities,
    garmin_to_ride,
    get_authorization_url,
    get_valid_token,
    revoke_token,
    store_token,
)


class TestGarminOAuth:
    def test_get_authorization_url_returns_dict(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_key", "test_key"),
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_redirect_uri", "https://test"),
        ):
            result = get_authorization_url()
            assert "auth_url" in result
            assert "state" in result
            assert "response_type=code" in result["auth_url"]
            assert "garmin.com" in result["auth_url"]

    def test_get_authorization_url_with_state(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_key", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_redirect_uri", "https://test"),
        ):
            result = get_authorization_url(state="custom_state")
            assert result["state"] == "custom_state"

    def test_get_authorization_url_missing_key(self):
        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_key", ""),
            pytest.raises(RuntimeError, match="GARMIN_CONSUMER_KEY"),
        ):
            get_authorization_url()

    @patch("bike_analyzer.backend.ingestion.garmin_client.request_json")
    async def test_exchange_code_for_token(self, mock_req):
        mock_req.return_value = {
            "access_token": "garmin_access",
            "refresh_token": "garmin_refresh",
            "expires_in": 3600,
        }

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_key", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_secret", "secret"),
            patch("bike_analyzer.backend.ingestion.garmin_client._GARMIN_TOKEN_URL", "https://test"),
        ):
            result = await exchange_code_for_token("auth_code")
            assert result["access_token"] == "garmin_access"

    @patch("bike_analyzer.backend.ingestion.garmin_client.request_json")
    async def test_exchange_code_raises_on_error(self, mock_req):
        mock_req.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=httpx.Request("POST", "https://test"),
            response=httpx.Response(401),
        )

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_key", "test"),
            patch("bike_analyzer.backend.ingestion.garmin_client._s.garmin_consumer_secret", "secret"),
            patch("bike_analyzer.backend.ingestion.garmin_client._GARMIN_TOKEN_URL", "https://test"),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await exchange_code_for_token("bad_code")


class TestGarminActivities:
    @patch("bike_analyzer.backend.ingestion.garmin_client.request_json")
    async def test_fetch_activities(self, mock_req):
        mock_req.return_value = [
            {"activityId": 1, "activityName": "Morning Ride", "startTimeGMT": "2024-06-15T08:00:00.000Z"},
        ]

        with (
            patch("bike_analyzer.backend.ingestion.garmin_client._GARMIN_API_BASE_URL", "https://test"),
            patch("bike_analyzer.backend.ingestion.garmin_client.store_token"),
        ):
            activities = await fetch_activities("access_token_123")
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

    def test_garmin_to_ride_non_cycling(self):
        activity = {
            "activityType": "running",
            "startTimeLocal": "2024-06-15T08:00:00.000Z",
            "distance": 5000,
            "duration": 1800,
        }
        ride = garmin_to_ride(activity)
        assert "error" in ride
        assert ride.get("skipped") is True


class TestGarminTokenStorage:
    def test_ensure_garmin_table(self):
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        with patch("bike_analyzer.backend.ingestion.garmin_client._get_conn", return_value=mock_conn):
            _ensure_garmin_table()
            mock_conn.executescript.assert_called_once()
            script = mock_conn.executescript.call_args[0][0]
            assert "CREATE TABLE IF NOT EXISTS garmin_tokens" in script

    def test_store_token_with_expires_in(self):
        with patch("bike_analyzer.backend.db.database.save_garmin_token") as mock_save:
            with patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x):
                store_token(1, {"access_token": "acc", "refresh_token": "ref", "expires_in": 3600})
            mock_save.assert_called_once()
            call_args = mock_save.call_args[1]
            assert call_args["athlete_id"] == 1
            assert call_args["access_token"] == "acc"
            assert call_args["refresh_token"] == "ref"

    def test_store_token_with_expires_at(self):
        with patch("bike_analyzer.backend.db.database.save_garmin_token") as mock_save:
            with patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x):
                store_token(1, {"access_token": "acc", "refresh_token": "ref", "expires_at": 1719560000})
            mock_save.assert_called_once()
            call_args = mock_save.call_args[1]
            assert call_args["expires_at"] == 1719560000

    def test_revoke_token(self):
        with patch("bike_analyzer.backend.db.database.revoke_garmin_token") as mock_revoke:
            revoke_token(1)
            mock_revoke.assert_called_once_with(1)

    async def test_get_valid_token_no_token(self):
        with patch("bike_analyzer.backend.db.database.get_garmin_token", return_value=None):
            result = await get_valid_token(1)
            assert result is None

    async def test_get_valid_token_fresh(self):
        with patch("bike_analyzer.backend.db.database.get_garmin_token", return_value={
            "access_token": "access_token_123",
            "refresh_token": "refresh",
            "expires_at": int(time.time()) + 7200,
        }):
            with patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x):
                result = await get_valid_token(1)
            assert result == "access_token_123"

    async def test_get_valid_token_refreshes_when_expired(self):
        with (
            patch("bike_analyzer.backend.db.database.get_garmin_token", return_value={
                "access_token": "old_token",
                "refresh_token": "refresh_token",
                "expires_at": int(time.time()) - 100,
            }),
            patch(
                "bike_analyzer.backend.ingestion.garmin_client.refresh_access_token",
                new=AsyncMock(return_value={"access_token": "new_token", "expires_in": 3600}),
            ) as mock_refresh,
        ):
            with patch("bike_analyzer.backend.db.token_crypto.decrypt_token", side_effect=lambda x: x):
                with patch("bike_analyzer.backend.db.token_crypto.encrypt_token", side_effect=lambda x: x):
                    result = await get_valid_token(1)
            assert result == "new_token"
            mock_refresh.assert_called_once_with("refresh_token")
