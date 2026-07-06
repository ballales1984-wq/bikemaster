import json
from pathlib import Path

from bike_analyzer.backend.audit_log import log_action, read_audit_logs


def test_log_action_writes_jsonl(tmp_path, monkeypatch):
    log_file = tmp_path / "audit.jsonl"
    monkeypatch.setattr("bike_analyzer.backend.audit_log._AUDIT_LOG_PATH", log_file)

    log_action(actor_id=1, action="backup", resource="database", resource_id=5, details={"file": "backup.db"})

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["actor_id"] == 1
    assert event["action"] == "backup"
    assert event["resource"] == "database"
    assert event["resource_id"] == 5
    assert "timestamp" in event


def test_read_audit_logs_returns_reversed(tmp_path, monkeypatch):
    log_file = tmp_path / "audit.jsonl"
    monkeypatch.setattr("bike_analyzer.backend.audit_log._AUDIT_LOG_PATH", log_file)

    for i in range(5):
        log_action(actor_id=i, action="test", resource="sys")

    logs = read_audit_logs(limit=3)
    assert len(logs) == 3
    assert logs[0]["actor_id"] == 4
    assert logs[1]["actor_id"] == 3
    assert logs[2]["actor_id"] == 2


def test_read_audit_logs_empty_when_missing(tmp_path, monkeypatch):
    missing = tmp_path / "missing.jsonl"
    monkeypatch.setattr("bike_analyzer.backend.audit_log._AUDIT_LOG_PATH", missing)
    assert read_audit_logs() == []


def test_log_action_handles_bad_path(monkeypatch):
    monkeypatch.setattr("bike_analyzer.backend.audit_log._AUDIT_LOG_PATH", Path("//invalid/path/audit.jsonl"))
    log_action(1, "x", "y")
