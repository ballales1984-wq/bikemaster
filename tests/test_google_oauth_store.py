"""Tests for google_oauth_store module."""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

from bike_analyzer.backend.ingestion.google_oauth_store import (
    ensure_google_tokens_table,
    get_google_token,
    get_valid_google_token,
    refresh_google_token,
    store_google_token,
)

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")


@pytest.fixture(autouse=True)
def _db_path(db_path):
    import bike_analyzer.backend.db.database as db_mod

    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()


def test_store_and_get_token(db_path):
    ensure_google_tokens_table()
    store_google_token(
        1,
        "google_fit",
        {
            "access_token": "at_123",
            "refresh_token": "rt_123",
            "expires_at": int(time.time()) + 3600,
            "scope": "fitness.activity.read",
        },
    )
    row = get_google_token(1, "google_fit")
    assert row is not None
    assert row["access_token"] == "at_123"
    assert row["refresh_token"] == "rt_123"
    assert row["scope"] == "fitness.activity.read"


def test_get_missing_token_returns_none(db_path):
    ensure_google_tokens_table()
    assert get_google_token(99, "google_health") is None


def test_get_valid_token_when_not_expired(db_path):
    ensure_google_tokens_table()
    store_google_token(
        1,
        "google_health",
        {
            "access_token": "at_456",
            "refresh_token": "rt_456",
            "expires_at": int(time.time()) + 3600,
        },
    )
    token = get_valid_google_token(1, "google_health")
    assert token == "at_456"


def test_get_valid_token_refreshes_when_expired(db_path):
    ensure_google_tokens_table()
    store_google_token(
        1,
        "google_fit",
        {
            "access_token": "at_old",
            "refresh_token": "rt_456",
            "expires_at": int(time.time()) - 100,
        },
    )
    new_token = "at_new"
    mock_response = type(
        "Resp",
        (),
        {
            "status_code": 200,
            "json": lambda self: {"access_token": new_token, "expires_in": 3600},
            "raise_for_status": lambda self: None,
        },
    )()
    with patch("requests.post", return_value=mock_response):
        token = get_valid_google_token(1, "google_fit")
    assert token == new_token


def test_refresh_google_token_invalid_grant_deletes_row(db_path):
    ensure_google_tokens_table()
    store_google_token(
        1,
        "google_health",
        {
            "access_token": "at_old",
            "refresh_token": "rt_bad",
            "expires_at": int(time.time()) - 100,
        },
    )
    import requests

    mock_response = type(
        "Resp",
        (),
        {
            "status_code": 400,
            "text": "invalid_grant",
        },
    )()
    exc = requests.HTTPError()
    exc.response = mock_response
    with patch("requests.post", side_effect=exc):
        result = refresh_google_token(1, "google_health")
    assert result is None
    assert get_google_token(1, "google_health") is None
