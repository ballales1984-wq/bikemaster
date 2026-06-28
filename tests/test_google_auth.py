"""Tests for Google OAuth authentication."""

from unittest.mock import MagicMock, patch

import pytest

from bike_analyzer.backend.auth.google_auth import (
    create_google_session,
    exchange_google_code,
    get_google_oauth_url,
    get_google_user_info,
)


class TestGetGoogleOAuthUrl:
    def test_basic_url(self):
        url = get_google_oauth_url("test_client_id")
        assert "accounts.google.com" in url
        assert "client_id=test_client_id" in url

    def test_custom_redirect_uri(self):
        url = get_google_oauth_url("test_client_id", redirect_uri="https://example.com/callback")
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in url

    def test_custom_state(self):
        url = get_google_oauth_url("test_client_id", state="csrf_token")
        assert "state=csrf_token" in url

    def test_url_contains_required_scopes(self):
        url = get_google_oauth_url("test_client_id")
        assert "scope=openid+email+profile" in url or "scope=openid%20email%20profile" in url

    def test_response_type_code(self):
        url = get_google_oauth_url("test_client_id")
        assert "response_type=code" in url

    def test_access_type_offline(self):
        url = get_google_oauth_url("test_client_id")
        assert "access_type=offline" in url


class TestExchangeGoogleCode:
    @patch("requests.post")
    def test_exchange_code(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "access_token": "google_access",
            "refresh_token": "google_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_resp

        result = exchange_google_code("client_id", "secret", "auth_code", "https://callback")
        assert result["access_token"] == "google_access"

    @patch("requests.post")
    def test_exchange_code_raises_on_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.raise_for_status.side_effect = Exception("Bad request")
        mock_post.return_value = mock_resp

        with pytest.raises(Exception):
            exchange_google_code("client_id", "secret", "bad_code", "https://callback")


class TestGetGoogleUserInfo:
    @patch("requests.get")
    def test_get_user_info(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            "sub": "12345",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }
        mock_get.return_value = mock_resp

        result = get_google_user_info("access_token_123")
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    @patch("requests.get")
    def test_get_user_info_raises_on_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_get.return_value = mock_resp

        with pytest.raises(Exception):
            get_google_user_info("invalid_token")


class TestCreateGoogleSession:
    @patch("bike_analyzer.backend.security.create_access_token")
    def test_create_session_with_athlete(self, mock_token):
        mock_token.return_value = "jwt_token_here"
        user_info = {
            "sub": "user_123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/pic.jpg",
        }
        session = create_google_session(user_info, athlete_id=42)
        assert session["access_token"] == "jwt_token_here"
        assert session["user_id"] == "42"
        assert session["email"] == "test@example.com"
        assert session["token_type"] == "bearer"

    @patch("bike_analyzer.backend.security.create_access_token")
    def test_create_session_without_athlete(self, mock_token):
        mock_token.return_value = "jwt_token_here"
        user_info = {
            "sub": "user_123",
            "email": "test@example.com",
            "name": "Test User",
        }
        session = create_google_session(user_info)
        assert session["access_token"] == "jwt_token_here"
        assert session["user_id"] == "user_123"
        assert session["email"] == "test@example.com"
