"""Tests for the synchronous UserRepository methods (local-first SQLite)."""

from __future__ import annotations

import sqlite3

from bike_analyzer.backend.analytics.repositories.user_repository import UserRepository


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    conn.commit()
    return conn


def _repo():
    return UserRepository(session_factory=None, sync_conn=_make_conn())


def test_save_returns_id():
    repo = _repo()
    uid = repo._save_sync({"username": "alice", "email": "a@test.it", "is_admin": False})
    assert isinstance(uid, int)
    assert uid > 0


def test_save_stores_fields():
    repo = _repo()
    uid = repo._save_sync(
        {
            "username": "bob",
            "email": "b@test.it",
            "password_hash": "secret",
            "is_admin": True,
            "is_active": False,
        }
    )
    row = repo._get_by_id_sync(uid)
    assert row["username"] == "bob"
    assert row["email"] == "b@test.it"
    assert row["password_hash"] == "secret"
    assert row["is_admin"] == 1
    assert row["is_active"] == 0
    assert row["created_at"] is not None
    assert row["updated_at"] is not None


def test_get_by_id_missing_returns_none():
    repo = _repo()
    assert repo._get_by_id_sync(999) is None


def test_get_by_username():
    repo = _repo()
    uid = repo._save_sync({"username": "carol", "email": "c@test.it"})
    row = repo._get_by_username_sync("carol")
    assert row is not None
    assert row["id"] == uid


def test_get_by_username_missing_returns_none():
    repo = _repo()
    assert repo._get_by_username_sync("nobody") is None


def test_get_by_email():
    repo = _repo()
    repo._save_sync({"username": "dave", "email": "d@test.it"})
    row = repo._get_by_email_sync("d@test.it")
    assert row is not None
    assert row["username"] == "dave"


def test_get_by_email_missing_returns_none():
    repo = _repo()
    assert repo._get_by_email_sync("missing@test.it") is None


def test_list_all():
    repo = _repo()
    repo._save_sync({"username": "u1", "email": "u1@test.it"})
    repo._save_sync({"username": "u2", "email": "u2@test.it"})
    all_users = repo._list_all_sync()
    assert len(all_users) == 2
    usernames = {u["username"] for u in all_users}
    assert usernames == {"u1", "u2"}
