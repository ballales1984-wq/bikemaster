"""Tests for ingestion/strava_client.py — Strava OAuth and activity import."""

from __future__ import annotations

import base64
import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from bike_analyzer.backend.ingestion.strava_client import (
    _STRAVA_PER_PAGE,
    _ensure_token_table,
    build_authorization_url,
    exchange_code_for_token,
    fetch_activities,
    fetch_all_activities,
    generate_code_challenge,
    generate_code_verifier,
    get_authorization_url,
    get_valid_token,
    refresh_access_token,
    revoke_token,
    store_token,
    strava_to_ride,
)


class TestPkceHelpers:
    def test_generate_code_verifier(self):
        v = generate_code_verifier()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_generate_code_challenge(self):
        verifier = "test_verifier_123"
        challenge = generate_code_challenge(verifier)
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        assert challenge == expected

    def test_code_challenge_format(self):
        verifier = generate_code_verifier()
        challenge = generate_code_challenge(verifier)
        assert "=" not in challenge
        assert "+" not in challenge
        assert "/" not in challenge


class TestBuildAuthorizationUrl:
    def test_returns_url(self):
        url = build_authorization_url("state123", "challenge456")
        assert "strava.com" in url
        assert "state123" in url
        assert "challenge456" in url

    def test_contains_required_params(self):
        url = build_authorization_url("s", "c")
        assert "client_id=" in url
        assert "response_type=code" in url
        assert "code_challenge_method=S256" in url


class TestGetAuthorizationUrl:
    def test_raises_without_client_id(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_CLIENT_ID", ""):
            with pytest.raises(RuntimeError, match="STRAVA_CLIENT_ID not configured"):
                get_authorization_url()

    def test_returns_expected_keys(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_CLIENT_ID", "test_id"):
            result = get_authorization_url()
            assert "auth_url" in result
            assert "state" in result
            assert "code_verifier" in result

    def test_uses_provided_state(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_CLIENT_ID", "test_id"):
            result = get_authorization_url(state="custom_state")
            assert result["state"] == "custom_state"

    def test_generates_unique_verifiers(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.STRAVA_CLIENT_ID", "test_id"):
            r1 = get_authorization_url()
            r2 = get_authorization_url()
            assert r1["code_verifier"] != r2["code_verifier"]


class TestExchangeCodeForToken:
    def test_posts_to_token_url(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "abc", "refresh_token": "def", "expires_at": 9999999999}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp
            result = exchange_code_for_token("code123", "verifier123")
            assert result["access_token"] == "abc"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["data"]["code"] == "code123"
            assert call_args[1]["data"]["code_verifier"] == "verifier123"


class TestRefreshAccessToken:
    def test_refreshes_token(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "new_token", "refresh_token": "new_refresh", "expires_in": 21600}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp
            result = refresh_access_token("old_refresh")
            assert result["access_token"] == "new_token"
            assert "refresh_token" in result
            assert "expires_in" in result


class TestTokenStorage:
    def _make_token_data(self) -> dict:
        return {
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "expires_at": int(time.time()) + 3600,
            "scope": "read,activity:read",
            "athlete": {"firstname": "John", "lastname": "Doe"},
        }

    def test_store_token_inserts(self, tmp_path):
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, self._make_token_data())
            conn.execute.assert_called()
            call_args = conn.execute.call_args[0]
            assert "INSERT INTO strava_tokens" in call_args[0]
            assert call_args[1][0] == 1

    def test_store_token_handles_string_expires_at(self, tmp_path):
        data = self._make_token_data()
        data["expires_at"] = "1234567890"
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, data)
            call_args = conn.execute.call_args[0]
            assert call_args[1][3] == 1234567890

    def test_store_token_calculates_from_expires_in(self, tmp_path):
        data = self._make_token_data()
        del data["expires_at"]
        data["expires_in"] = 7200
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, data)
            call_args = conn.execute.call_args[0]
            stored_expires = call_args[1][3]
            assert stored_expires > int(time.time())

    def test_revoke_token_deletes(self, tmp_path):
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            revoke_token(42)
            call_args = conn.execute.call_args[0]
            assert "DELETE FROM strava_tokens WHERE athlete_id = ?" in call_args[0]

    def test_get_valid_token_returns_none_when_missing(self):
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = None
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            assert get_valid_token(99) is None

    def test_get_valid_token_returns_access(self):
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = ("access_token_xyz", "refresh_xyz", int(time.time()) + 7200)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            assert get_valid_token(1) == "access_token_xyz"

    def test_get_valid_token_refreshes_when_expired(self):
        with patch("bike_analyzer.backend.ingestion.strava_client._get_conn") as mock_get_conn, \
             patch("bike_analyzer.backend.ingestion.strava_client.refresh_access_token") as mock_refresh:
            conn = MagicMock()
            expired_ts = int(time.time()) - 100
            conn.execute.return_value.fetchone.return_value = ("old_token", "refresh_xyz", expired_ts)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            mock_refresh.return_value = {"access_token": "new_token", "refresh_token": "new_refresh", "expires_in": 21600}
            token = get_valid_token(1)
            assert token == "new_token"
            mock_refresh.assert_called_once_with("refresh_xyz")


class TestFetchActivities:
    def test_fetches_with_auth_header(self):
        with patch("bike_analyzer.backend.ingestion.strava_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"id": 1, "name": "Ride"}]
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp
            activities = fetch_activities("token_xyz", page=2, per_page=20)
            assert len(activities) == 1
            assert activities[0]["name"] == "Ride"
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer token_xyz"
            assert call_kwargs["params"]["page"] == 2

    def test_fetch_all_paginates(self):
        page_sizes = [30, 30, 10]

        def mock_get(*args, **kwargs):
            page = kwargs.get("params", {}).get("page", 1)
            resp = MagicMock()
            resp.json.return_value = [{"id": page}] * page_sizes[page - 1]
            resp.raise_for_status.return_value = None
            return resp

        with patch("bike_analyzer.backend.ingestion.strava_client.requests.get", side_effect=mock_get):
            activities = fetch_all_activities("token_xyz", max_pages=5)
            assert len(activities) == 70

    def test_fetch_all_stops_on_empty_page(self):
        def mock_get(*args, **kwargs):
            resp = MagicMock()
            resp.json.return_value = []
            resp.raise_for_status.return_value = None
            return resp

        with patch("bike_analyzer.backend.ingestion.strava_client.requests.get", side_effect=mock_get):
            activities = fetch_all_activities("token_xyz")
            assert activities == []


class TestStravaToRide:
    def test_basic_ride(self):
        activity = {
            "id": 12345,
            "name": "Morning Ride",
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 50000,
            "moving_time": 7200,
            "average_speed": 6.944,
            "calories": 800,
            "total_elevation_gain": 300.5,
            "average_heartrate": 155.0,
        }
        ride = strava_to_ride(activity, weight_kg=70.0)
        assert ride["date"] == "2024-06-15"
        assert ride["distance_km"] == 50.0
        assert ride["duration_minutes"] == 120.0
        assert abs(ride["avg_speed_kmh"] - 25.0) < 0.1
        assert ride["calories"] == 800
        assert ride["elevation_gain_m"] == 300.5
        assert ride["heart_rate_avg"] == 155.0
        assert ride["external_source"] == "strava"
        assert ride["external_id"] == "12345"
        assert ride["title"] == "Morning Ride"

    def test_zero_values(self):
        activity = {
            "id": 1,
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 0,
            "moving_time": 0,
            "average_speed": 0,
        }
        ride = strava_to_ride(activity)
        assert ride["distance_km"] == 0.0
        assert ride["duration_minutes"] == 0.0
        assert ride["avg_speed_kmh"] == 0.0

    def test_skips_non_bike_activity(self):
        activity = {
            "id": 1,
            "name": "Run",
            "sport_type": "Run",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 10000,
            "moving_time": 3600,
        }
        ride = strava_to_ride(activity)
        assert "error" in ride
        assert ride["skipped"] is True

    def test_none_heart_rate(self):
        activity = {
            "id": 1,
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 50000,
            "moving_time": 3600,
            "average_speed": 14.0,
            "average_heartrate": None,
        }
        ride = strava_to_ride(activity)
        assert ride["heart_rate_avg"] is None

    def test_alternative_type_field(self):
        activity = {
            "id": 1,
            "name": "Ride",
            "type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 50000,
            "moving_time": 3600,
            "average_speed": 14.0,
        }
        ride = strava_to_ride(activity)
        assert "error" not in ride

    def test_weight_kg_default(self):
        activity = {
            "id": 1,
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 30000,
            "moving_time": 3600,
            "average_speed": 8.33,
        }
        ride = strava_to_ride(activity)
        assert ride["weight_kg"] == 70.0

    def test_calories_defaults_to_zero(self):
        activity = {
            "id": 1,
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 30000,
            "moving_time": 3600,
            "average_speed": 8.33,
        }
        ride = strava_to_ride(activity)
        assert ride["calories"] == 0

    def test_gps_points_empty(self):
        activity = {
            "id": 1,
            "sport_type": "Ride",
            "start_date_local": "2024-06-15T08:00:00Z",
            "distance": 30000,
            "moving_time": 3600,
            "average_speed": 8.33,
        }
        ride = strava_to_ride(activity)
        assert ride["gps_points"] == []
