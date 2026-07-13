"""Tests for the JSONL-backed conversation store."""

from __future__ import annotations

import json

import pytest

import bike_analyzer.backend.analytics.conversation_store as cs
from bike_analyzer.backend.analytics.conversation_store import append, load, prune


@pytest.fixture
def tmp_conversation_log(tmp_path, monkeypatch):
    path = tmp_path / "conversations.jsonl"
    monkeypatch.setattr(cs, "_CONVERSATION_LOG_PATH", path)
    return path


def test_load_returns_empty_when_file_missing(tmp_path, monkeypatch):
    path = tmp_path / "nonexistent.jsonl"
    monkeypatch.setattr(cs, "_CONVERSATION_LOG_PATH", path)
    assert load(1) == []


def test_append_and_load(tmp_conversation_log):
    append(1, {"role": "user", "content": "Ciao"})
    append(1, {"role": "assistant", "content": "Ciao! Come posso aiutarti?"})
    messages = load(1)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Ciao"
    assert messages[1]["role"] == "assistant"
    assert "user_id" in messages[0]


def test_load_isolates_users(tmp_conversation_log):
    append(1, {"role": "user", "content": "Da utente 1"})
    append(2, {"role": "user", "content": "Da utente 2"})
    assert len(load(1)) == 1
    assert len(load(2)) == 1
    assert load(1)[0]["content"] == "Da utente 1"
    assert load(2)[0]["content"] == "Da utente 2"


def test_prune_removes_excess_messages(tmp_conversation_log):
    for i in range(10):
        append(1, {"role": "user", "content": f"msg {i}"})
    removed = prune(1, max_len=5)
    assert removed == 5
    remaining = load(1)
    assert len(remaining) == 5
    assert remaining[0]["content"] == "msg 5"
    assert remaining[-1]["content"] == "msg 9"


def test_prune_is_noop_under_limit(tmp_conversation_log):
    append(1, {"role": "user", "content": "msg"})
    removed = prune(1, max_len=50)
    assert removed == 0
    assert len(load(1)) == 1


def test_prune_does_not_affect_other_users(tmp_conversation_log):
    for i in range(10):
        append(1, {"role": "user", "content": f"u1-{i}"})
        append(2, {"role": "user", "content": f"u2-{i}"})
    prune(1, max_len=3)
    assert len(load(1)) == 3
    assert len(load(2)) == 10


def test_prune_skips_corrupt_lines(tmp_conversation_log):
    with cs._CONVERSATION_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"user_id": "1", "role": "user", "content": "ok"}) + "\n")
        f.write("not-json\n")
        f.write(json.dumps({"user_id": "2", "role": "user", "content": "other"}) + "\n")
        f.write(json.dumps({"user_id": "1", "role": "user", "content": "keep"}) + "\n")
    prune(1, max_len=1)
    remaining = load(1)
    assert len(remaining) == 1
    assert remaining[0]["content"] == "keep"
    assert len(load(2)) == 1
