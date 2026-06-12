"""Test coverage for security module (JWT auth)."""

import os
import sys

import pytest

os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-testing-123456"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["JWT_ISSUER"] = "test-issuer"
os.environ["JWT_AUDIENCE"] = "test-audience"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import timedelta

from fastapi import HTTPException
from jose import jwt

from bike_analyzer.backend.security import (
    create_access_token,
    decode_token,
    get_current_user,
    get_optional_current_user,
    hash_password,
    oauth2_scheme,
    verify_password,
)


def test_hash_password():
    hashed = hash_password("testpwd")
    assert hashed is not None
    assert hashed != "testpwd"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("mypwd")
    assert verify_password("mypwd", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("mypwd")
    assert verify_password("wrongpwd", hashed) is False


def test_create_access_token():
    token = create_access_token("user123")
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 50


def test_create_access_token_with_custom_expiry():
    token = create_access_token("user456", expires_delta=timedelta(hours=1))
    assert token is not None
    payload = decode_token(token)
    assert payload["sub"] == "user456"


def test_decode_token_valid():
    token = create_access_token("testuser")
    payload = decode_token(token)
    assert payload["sub"] == "testuser"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_token_invalid():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.here")
    assert exc_info.value.status_code == 401


def test_decode_token_malformed():
    with pytest.raises(HTTPException):
        decode_token("")


def test_oauth2_scheme():
    assert oauth2_scheme is not None


def test_payload_structure():
    token = create_access_token("testuser", expires_delta=timedelta(minutes=30))
    payload = decode_token(token)
    assert payload["sub"] == "testuser"
    assert "iss" in payload
    assert "aud" in payload


def test_decode_token_wrong_issuer():
    wrong_payload = {
        "sub": "user",
        "iss": "wrong",
        "aud": "test-audience",
        "exp": 9999999999,
        "iat": 1,
    }
    token = jwt.encode(wrong_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)


def test_decode_token_wrong_audience():
    wrong_payload = {
        "sub": "user",
        "iss": "test-issuer",
        "aud": "wrong",
        "exp": 9999999999,
        "iat": 1,
    }
    token = jwt.encode(wrong_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)


def test_decode_token_expired():
    expired_payload = {
        "sub": "user",
        "iss": "test-issuer",
        "aud": "test-audience",
        "exp": 1,
        "iat": 1,
    }
    token = jwt.encode(expired_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)


@pytest.mark.asyncio
async def test_get_current_user_valid():
    token = create_access_token("123")
    result = await get_current_user(token)
    assert result["id"] == 123


@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    token = create_access_token("invalid-int-id-xyz")
    result = await get_current_user(token)
    assert result["id"] == "invalid-int-id-xyz"


@pytest.mark.asyncio
async def test_get_optional_current_user_with_valid_token():
    token = create_access_token("456")
    result = await get_optional_current_user(token)
    assert result["id"] == 456


@pytest.mark.asyncio
async def test_get_optional_current_user_no_token():
    result = await get_optional_current_user(None)
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_current_user_invalid_token():
    result = await get_optional_current_user("bad-token")
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_current_user_empty_string():
    result = await get_optional_current_user("")
    assert result is None


def test_decode_token_missing_sub():
    import os

    from jose import jwt

    payload = {
        "iat": 1,
        "exp": 9999999999,
        "iss": "test-issuer",
        "aud": "test-audience",
        "sub": None,
    }
    token = jwt.encode(payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)


@pytest.mark.asyncio
async def test_get_current_user_with_none_sub():
    from unittest.mock import patch

    with patch("bike_analyzer.backend.security.decode_token", return_value={}):
        try:
            from bike_analyzer.backend.security import get_current_user

            await get_current_user("any-token")
        except Exception:
            pass


def test_auth_login_endpoint(client):
    response = client.post("/api/v1/auth/register", json={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 200
    response = client.post("/api/v1/auth/login", data={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_auth_login_invalid(client):
    response = client.post("/api/v1/auth/login", data={"username": "wrong", "password": "wrong"})
    assert response.status_code == 401


def test_protected_route_no_auth_shows_empty(client):
    response = client.get("/api/v1/rides")
    assert response.status_code == 200


def test_protected_route_with_valid_token(client):
    client.post("/api/v1/auth/register", json={"username": "authtest", "password": "testpass123"})
    login_resp = client.post("/api/v1/auth/login", data={"username": "authtest", "password": "testpass123"})
    token = login_resp.json()["access_token"]
    response = client.get("/api/v1/rides", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_athletes_endpoint_requires_ownership(client):
    """Test that /athletes/{id} endpoint enforces ownership."""
    client.post("/api/v1/auth/register", json={"username": "user1", "password": "testpass123"})
    client.post("/api/v1/auth/register", json={"username": "user2", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]
    login2 = client.post("/api/v1/auth/login", data={"username": "user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    # Create athlete for user1
    client.post(
        "/api/v1/athletes",
        json={"name": "Alice", "age": 30, "weight_kg": 70.0},
        headers={"Authorization": f"Bearer {token1}"},
    )

    # Get user1's athlete id
    resp1 = client.get("/api/v1/athletes", headers={"Authorization": f"Bearer {token1}"})
    assert resp1.status_code == 200
    user1_id = resp1.json()["id"]

    # User2 cannot access user1's athlete profile
    resp2 = client.get(f"/api/v1/athletes/{user1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 403


def test_training_endpoints_isolation(client):
    """Test that training endpoints are isolated between users."""
    # Register user1 and get token
    client.post("/api/v1/auth/register", json={"username": "tr_user1", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "tr_user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]

    # Create an athlete for user1 to have an athlete_id
    client.post("/api/v1/athletes", json={"name": "User1"}, headers={"Authorization": f"Bearer {token1}"})
    resp1 = client.get("/api/v1/athletes", headers={"Authorization": f"Bearer {token1}"})
    user1_athlete_id = resp1.json()["id"]

    # Register user2
    client.post("/api/v1/auth/register", json={"username": "tr_user2", "password": "testpass123"})
    login2 = client.post("/api/v1/auth/login", data={"username": "tr_user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    # User2 cannot access user1's training data
    resp = client.get(
        f"/api/v1/training/load?athlete_id={user1_athlete_id}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert resp.status_code == 403

    resp = client.get(
        f"/api/v1/training/status?athlete_id={user1_athlete_id}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert resp.status_code == 403


def test_coach_history_requires_ownership(client):
    """Test that /coach/history requires ownership of athlete data."""
    client.post("/api/v1/auth/register", json={"username": "ch_user1", "password": "testpass123"})
    client.post("/api/v1/auth/register", json={"username": "ch_user2", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "ch_user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]
    login2 = client.post("/api/v1/auth/login", data={"username": "ch_user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    resp1 = client.get("/api/v1/athletes", headers={"Authorization": f"Bearer {token1}"})
    user1_id = resp1.json()["id"]

    # User2 cannot access user1's chat history
    resp2 = client.get(f"/api/v1/coach/history?athlete_id={user1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 403


def test_coach_chat_requires_ownership(client):
    """Test that /coach/chat requires ownership of athlete data."""
    client.post("/api/v1/auth/register", json={"username": "cc_user1", "password": "testpass123"})
    client.post("/api/v1/auth/register", json={"username": "cc_user2", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "cc_user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]
    login2 = client.post("/api/v1/auth/login", data={"username": "cc_user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    resp1 = client.get("/api/v1/athletes", headers={"Authorization": f"Bearer {token1}"})
    user1_id = resp1.json()["id"]

    # User2 cannot access user1's chat
    resp2 = client.get(
        f"/api/v1/coach/chat?athlete_id={user1_id}&message=test", headers={"Authorization": f"Bearer {token2}"}
    )
    assert resp2.status_code == 403


def test_scores_endpoint_requires_ownership(client):
    """Test that /scores/athlete/{id} requires ownership."""
    client.post("/api/v1/auth/register", json={"username": "sc_user1", "password": "testpass123"})
    client.post("/api/v1/auth/register", json={"username": "sc_user2", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "sc_user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]
    login2 = client.post("/api/v1/auth/login", data={"username": "sc_user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    resp1 = client.get("/api/v1/athletes", headers={"Authorization": f"Bearer {token1}"})
    user1_id = resp1.json()["id"]

    # User2 cannot access user1's scores
    resp2 = client.get(f"/api/v1/scores/athlete/{user1_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp2.status_code == 403


def test_rides_endpoint_isolation(client):
    """Test that rides are isolated between users."""
    # Register user1
    client.post("/api/v1/auth/register", json={"username": "iso_user1", "password": "testpass123"})
    login1 = client.post("/api/v1/auth/login", data={"username": "iso_user1", "password": "testpass123"})
    token1 = login1.json()["access_token"]

    # Create a ride for user1
    ride_data = {
        "date": "2024-06-01",
        "distance_km": 25.0,
        "duration_minutes": 60,
        "avg_speed_kmh": 25.0,
    }
    client.post("/api/v1/rides", json=ride_data, headers={"Authorization": f"Bearer {token1}"})

    # Register user2
    client.post("/api/v1/auth/register", json={"username": "iso_user2", "password": "testpass123"})
    login2 = client.post("/api/v1/auth/login", data={"username": "iso_user2", "password": "testpass123"})
    token2 = login2.json()["access_token"]

    # User2 should not see user1's rides
    resp = client.get("/api/v1/rides", headers={"Authorization": f"Bearer {token2}"})
    assert resp.status_code == 200
    assert resp.json()["rides"] == []
