"""Tests for ingestion/wahoo_client.py — Wahoo OAuth and workout import."""

from __future__ import annotations

import hashlib
import time
from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.ingestion import wahoo_client
from bike_analyzer.backend.ingestion.wahoo_client import (
    build_authorization_url,
    exchange_code_for_token,
    fetch_workouts,
    generate_code_challenge,
    generate_code_verifier,
    get_authorization_url,
    get_valid_token,
    refresh_access_token,
    revoke_token,
    store_token,
    wahoo_to_ride,
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
        import base64

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
        url = build_authorization_url("state123", "challenge456", client_id="test_id")
        assert "wahooligan.com" in url
        assert "state123" in url
        assert "challenge456" in url

    def test_contains_required_params(self):
        url = build_authorization_url("s", "c", client_id="test_id")
        assert "client_id=" in url
        assert "response_type=code" in url
        assert "code_challenge_method=S256" in url


class TestGetAuthorizationUrl:
    def test_raises_without_client_id(self, monkeypatch):
        monkeypatch.setattr(wahoo_client._s, "wahoo_client_id", "")
        with pytest.raises(RuntimeError, match="WAHOO_CLIENT_ID not configured"):
            get_authorization_url()

    def test_returns_expected_keys(self, monkeypatch):
        monkeypatch.setattr(wahoo_client._s, "wahoo_client_id", "test_id")
        result = get_authorization_url()
        assert "auth_url" in result
        assert "state" in result
        assert "code_verifier" in result

    def test_uses_provided_state(self, monkeypatch):
        monkeypatch.setattr(wahoo_client._s, "wahoo_client_id", "test_id")
        result = get_authorization_url(state="custom_state")
        assert result["state"] == "custom_state"

    def test_generates_unique_verifiers(self, monkeypatch):
        monkeypatch.setattr(wahoo_client._s, "wahoo_client_id", "test_id")
        r1 = get_authorization_url()
        r2 = get_authorization_url()
        assert r1["code_verifier"] != r2["code_verifier"]


class TestExchangeCodeForToken:
    def test_posts_to_token_url(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "abc", "refresh_token": "def", "expires_at": 9999999999}
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp
            result = exchange_code_for_token("code123", "verifier123", client_id="test_id", client_secret="test_secret")
            assert result["access_token"] == "abc"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["data"]["code"] == "code123"
            assert call_args[1]["data"]["code_verifier"] == "verifier123"


class TestRefreshAccessToken:
    def test_refreshes_token(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_in": 21600,
            }
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp
            result = refresh_access_token("old_refresh", "verifier", client_id="test_id", client_secret="test_secret")
            assert result["access_token"] == "new_token"
            assert "refresh_token" in result
            assert "expires_in" in result


class TestTokenStorage:
    def _make_token_data(self) -> dict:
        return {
            "access_token": "test_access",
            "refresh_token": "test_refresh",
            "code_verifier": "verifier",
            "expires_at": int(time.time()) + 3600,
            "scope": "read,workouts_read",
        }

    def test_store_token_inserts(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, self._make_token_data(), code_verifier="verifier")
            conn.execute.assert_called()
            call_args = conn.execute.call_args[0]
            assert "INSERT INTO wahoo_tokens" in call_args[0]
            assert call_args[1][0] == 1

    def test_store_token_handles_string_expires_at(self):
        data = self._make_token_data()
        data["expires_at"] = "1234567890"
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, data, code_verifier="verifier")
            call_args = conn.execute.call_args[0]
            assert call_args[1][4] == 1234567890

    def test_store_token_calculates_from_expires_in(self):
        data = self._make_token_data()
        del data["expires_at"]
        data["expires_in"] = 7200
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            store_token(1, data, code_verifier="verifier")
            call_args = conn.execute.call_args[0]
            stored_expires = call_args[1][4]
            assert stored_expires > int(time.time())

    def test_revoke_token_deletes(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            revoke_token(42)
            call_args = conn.execute.call_args[0]
            assert "DELETE FROM wahoo_tokens WHERE athlete_id = ?" in call_args[0]
            assert call_args[1][0] == 42

    def test_get_valid_token_returns_none_when_missing(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = None
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            assert get_valid_token(99) is None

    def test_get_valid_token_returns_access(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn:
            conn = MagicMock()
            conn.execute.return_value.fetchone.return_value = (
                "access_token_xyz",
                "refresh_xyz",
                "verifier",
                int(time.time()) + 7200,
            )
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            assert get_valid_token(1) == "access_token_xyz"

    def test_get_valid_token_refreshes_when_expired(self):
        with (
            patch("bike_analyzer.backend.ingestion.wahoo_client._get_conn") as mock_get_conn,
            patch("bike_analyzer.backend.ingestion.wahoo_client.refresh_access_token") as mock_refresh,
        ):
            conn = MagicMock()
            expired_ts = int(time.time()) - 100
            conn.execute.return_value.fetchone.return_value = ("old_token", "refresh_xyz", "verifier", expired_ts)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)
            mock_refresh.return_value = {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
                "expires_in": 21600,
            }
            token = get_valid_token(1, client_id="test_id", client_secret="test_secret")
            assert token == "new_token"
            mock_refresh.assert_called_once_with("refresh_xyz", "verifier", client_id="test_id", client_secret="test_secret")


class TestFetchWorkouts:
    def test_fetches_with_auth_header(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"id": 1, "name": "Morning Ride"}]
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp
            workouts = fetch_workouts("token_xyz")
            assert len(workouts) == 1
            assert workouts[0]["name"] == "Morning Ride"
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer token_xyz"

    def test_fetch_workouts_unwraps_dict(self):
        with patch("bike_analyzer.backend.ingestion.wahoo_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"workouts": [{"id": 1}]}
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp
            workouts = fetch_workouts("token_xyz")
            assert len(workouts) == 1


class TestWahooToRide:
    def test_basic_ride(self):
        workout = {
            "id": 12345,
            "name": "Morning",
            "starts": "2024-06-15T08:00:00.000Z",
            "workout_summary": {
                "distance_accum": "40000.0",
                "duration_active_accum": "2400.0",
                "speed_avg": "6.944",
                "calories_accum": "900.0",
                "ascent_accum": "250.5",
                "heart_rate_avg": "155.0",
                "name": "Morning Ride",
            },
        }
        ride = wahoo_to_ride(workout, weight_kg=70.0)
        assert ride["date"] == "2024-06-15"
        assert ride["distance_km"] == 40.0
        assert ride["duration_minutes"] == 40.0
        assert abs(ride["avg_speed_kmh"] - 25.0) < 0.1
        assert ride["calories"] == 900.0
        assert ride["elevation_gain_m"] == 250.5
        assert ride["heart_rate_avg"] == 155.0
        assert ride["external_source"] == "wahoo"
        assert ride["external_id"] == "12345"

    def test_missing_summary(self):
        workout = {"id": 1, "name": "Ride"}
        ride = wahoo_to_ride(workout)
        assert "error" in ride
        assert ride.get("skipped") is True

    def test_zero_values(self):
        workout = {
            "id": 1,
            "starts": "2024-06-15T08:00:00.000Z",
            "workout_summary": {
                "distance_accum": "0",
                "duration_active_accum": "0",
                "speed_avg": "0",
            },
        }
        ride = wahoo_to_ride(workout)
        assert ride["distance_km"] == 0.0
        assert ride["duration_minutes"] == 0.0
        assert ride["avg_speed_kmh"] == 0.0

    def test_none_heart_rate(self):
        workout = {
            "id": 1,
            "starts": "2024-06-15T08:00:00.000Z",
            "workout_summary": {
                "distance_accum": "20000.0",
                "duration_active_accum": "1800.0",
                "speed_avg": "5.0",
                "heart_rate_avg": None,
            },
        }
        ride = wahoo_to_ride(workout)
        assert ride["heart_rate_avg"] is None

    def test_gps_points_empty(self):
        workout = {
            "id": 1,
            "starts": "2024-06-15T08:00:00.000Z",
            "workout_summary": {
                "distance_accum": "10000.0",
                "duration_active_accum": "1200.0",
                "speed_avg": "3.0",
            },
        }
        ride = wahoo_to_ride(workout)
        assert ride["gps_points"] == []
