"""Tests for audit.py module."""

from __future__ import annotations

import json

import pytest

from bike_analyzer.backend.audit import log_action


@pytest.fixture
def tmp_audit_log(tmp_path):
    """Provide a temporary audit log file path."""
    log_path = str(tmp_path / "audit.jsonl")
    return log_path


class TestAuditLog:
    def test_log_action_writes_entry(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log
        log_action("user.login", actor="user_42", resource="session", details={"ip": "10.0.0.1"})

        with open(tmp_audit_log, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["action"] == "user.login"
        assert entry["actor"] == "user_42"
        assert entry["resource"] == "session"
        assert entry["details"]["ip"] == "10.0.0.1"
        assert "timestamp" in entry

    def test_log_action_minimal_fields(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log
        log_action("ride.deleted")

        with open(tmp_audit_log, encoding="utf-8") as f:
            lines = f.readlines()

        entry = json.loads(lines[0])
        assert entry["action"] == "ride.deleted"
        assert entry["actor"] is None
        assert entry["resource"] is None
        assert entry["details"] == {}

    def test_log_action_appends_multiple_entries(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log
        log_action("event.a", actor="a")
        log_action("event.b", actor="b")

        with open(tmp_audit_log, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["action"] == "event.a"
        assert json.loads(lines[1])["action"] == "event.b"

    def test_log_action_handles_unserializable_details(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log

        class _Unserializable:
            pass

        log_action("test", details={"obj": _Unserializable()})

        with open(tmp_audit_log, encoding="utf-8") as f:
            lines = f.readlines()

        entry = json.loads(lines[0])
        assert "obj" in entry["details"]

    def test_log_action_handles_write_failure(self, tmp_audit_log, monkeypatch, caplog):
        monkeypatch.setenv("AUDIT_LOG_PATH", "/nonexistent_dir/audit.jsonl")
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = "/nonexistent_dir/audit.jsonl"

        with caplog.at_level("WARNING"):
            log_action("test.action")

        assert "Failed to write audit log" in caplog.text

    def test_log_action_thread_safety(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log
        import threading

        def writer(n):
            log_action(f"thread.{n}", actor=f"user_{n}")

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(tmp_audit_log, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 10

    def test_timestamp_is_utc_isoformat(self, tmp_audit_log, monkeypatch):
        monkeypatch.setenv("AUDIT_LOG_PATH", tmp_audit_log)
        from bike_analyzer.backend import audit as audit_mod

        audit_mod.AUDIT_LOG_PATH = tmp_audit_log
        log_action("test")

        with open(tmp_audit_log, encoding="utf-8") as f:
            entry = json.loads(f.readline())

        ts = entry["timestamp"]
        assert ts.endswith("Z") or "+00:00" in ts
