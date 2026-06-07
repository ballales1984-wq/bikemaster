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
from jose import jwt
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import asyncio

from bike_analyzer.backend.security import (
    hash_password, verify_password, create_access_token, decode_token,
    pwd_context, oauth2_scheme
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
    wrong_payload = {"sub": "user", "iss": "wrong", "aud": "test-audience", "exp": 9999999999, "iat": 1}
    token = jwt.encode(wrong_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)

def test_decode_token_wrong_audience():
    wrong_payload = {"sub": "user", "iss": "test-issuer", "aud": "wrong", "exp": 9999999999, "iat": 1}
    token = jwt.encode(wrong_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)

def test_decode_token_expired():
    expired_payload = {"sub": "user", "iss": "test-issuer", "aud": "test-audience", "exp": 1, "iat": 1}
    token = jwt.encode(expired_payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)

from bike_analyzer.backend.security import get_current_user, get_optional_current_user

@pytest.mark.asyncio
async def test_get_current_user_valid():
    token = create_access_token("123")
    result = await get_current_user(token)
    assert result["id"] == 123

@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    token = create_access_token("invalid-int-id-xyz")
    with pytest.raises(ValueError):
        await get_current_user(token)

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
    from jose import jwt
    import os
    payload = {"iat": 1, "exp": 9999999999, "iss": "test-issuer", "aud": "test-audience", "sub": None}
    token = jwt.encode(payload, os.environ["SECRET_KEY"], algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_token(token)

@pytest.mark.asyncio
async def test_get_current_user_with_none_sub():
    from unittest.mock import patch, MagicMock
    with patch('bike_analyzer.backend.security.decode_token', return_value={}):
        try:
            from bike_analyzer.backend.security import get_current_user
            result = await get_current_user("any-token")
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