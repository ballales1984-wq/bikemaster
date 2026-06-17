"""Tests for Google OAuth integration."""
import os
from unittest.mock import MagicMock, Mock, patch

from jose import jwt

from bike_analyzer.backend.auth.google_auth import (
    create_google_session,
    exchange_google_code,
    get_google_oauth_url,
)


def test_get_google_oauth_url():
    url = get_google_oauth_url("test-client-id", "http://localhost:8000/callback")
    assert "accounts.google.com" in url
    assert "client_id=test-client-id" in url
    assert "redirect_uri=http" in url


def test_get_google_oauth_url_with_state():
    url = get_google_oauth_url("client", state="custom-state-123")
    assert "state=custom-state-123" in url


def test_exchange_google_code_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "test-token"}
    mock_response.raise_for_status = Mock()

    with patch("requests.post", return_value=mock_response):
        result = exchange_google_code("id", "secret", "code", "http://localhost/callback")
    assert result["access_token"] == "test-token"


def test_create_google_session():
    user_info = {"sub": "12345", "email": "test@example.com", "name": "Test User"}
    result = create_google_session(user_info)
    assert "access_token" in result
    assert result["user_id"] == "12345"
    assert result["email"] == "test@example.com"


def test_create_google_session_uses_athlete_id_as_jwt_subject():
    user_info = {"sub": "google-sub", "email": "test@example.com", "name": "Test User"}
    result = create_google_session(user_info, athlete_id=42)

    payload = jwt.decode(
        result["access_token"],
        os.environ["SECRET_KEY"],
        algorithms=["HS256"],
        issuer=os.environ["JWT_ISSUER"],
        audience=os.environ["JWT_AUDIENCE"],
    )

    assert result["user_id"] == "42"
    assert payload["sub"] == "42"