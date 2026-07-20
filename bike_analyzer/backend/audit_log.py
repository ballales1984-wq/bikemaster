"""Admin audit log for sensitive actions."""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_AUDIT_LOG_PATH = Path("logs/audit.jsonl")


def _ensure_log_dir() -> None:
    with contextlib.suppress(Exception):
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_action(
    actor_id: int | None,
    action: str,
    resource: str,
    resource_id: int | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit event to the JSONL log file."""
    _ensure_log_dir()
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "actor_id": actor_id,
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
    }
    try:
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("Audit log write failed: %s", exc)


def read_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Read the last ``limit`` audit events from the JSONL file.

    The file is scanned entirely and the lines are **reversed**
    (``reverse``) so that it returns the most recent events first; the rows
    unparsable (corrupted JSON) are skipped without interrupting reading.
    """
    if not _AUDIT_LOG_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    entries.reverse()
    return entries[:limit]


