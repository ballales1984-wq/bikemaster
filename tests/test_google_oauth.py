"""Tests for Google OAuth integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from bike_analyzer.backend.auth.google_auth import (
    get_google_oauth_url,
    exchange_google_code,
    create_google_session,
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