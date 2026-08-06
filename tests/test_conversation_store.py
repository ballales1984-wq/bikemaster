"""Tests for conversation store and audit log to improve coverage."""

from __future__ import annotations

import json

from bike_analyzer.backend.analytics.conversation_store import append, load, prune


class TestConversationStore:
    def test_load_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BIKEMASTER_DATA_DIR", str(tmp_path))
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        result = load(1)
        assert result == []

    def test_append_and_load(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        append(1, {"role": "user", "content": "hello"})
        result = load(1)
        assert len(result) == 1
        assert result[0]["content"] == "hello"
        assert result[0]["user_id"] == "1"

    def test_load_filters_by_user_id(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        append(1, {"role": "user", "content": "hello1"})
        append(2, {"role": "user", "content": "hello2"})
        result = load(1)
        assert len(result) == 1
        assert result[0]["content"] == "hello1"

    def test_append_preserves_created_at(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        append(1, {"role": "user", "content": "hello", "created_at": "2024-06-15T10:00:00"})
        result = load(1)
        assert result[0]["created_at"] == "2024-06-15T10:00:00"

    def test_prune_removes_old_messages(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        for i in range(10):
            append(1, {"role": "user", "content": f"msg{i}"})
        removed = prune(1, max_len=5)
        assert removed == 5
        result = load(1)
        assert len(result) == 5

    def test_prune_returns_zero_when_under_limit(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        append(1, {"role": "user", "content": "hello"})
        removed = prune(1, max_len=10)
        assert removed == 0

    def test_prune_returns_zero_when_no_file(self, tmp_path, monkeypatch):
        log_path = tmp_path / "nonexistent.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        removed = prune(1, max_len=5)
        assert removed == 0

    def test_load_handles_malformed_lines(self, tmp_path, monkeypatch):
        log_path = tmp_path / "conversations.jsonl"
        monkeypatch.setattr(
            "bike_analyzer.backend.analytics.conversation_store._CONVERSATION_LOG_PATH",
            log_path,
        )
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("not json\n")
            f.write(json.dumps({"user_id": "1", "content": "valid"}) + "\n")
        result = load(1)
        assert len(result) == 1
        assert result[0]["content"] == "valid"
