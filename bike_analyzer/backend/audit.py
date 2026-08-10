"""Simple audit log for admin actions.

Writes audit entries to a JSONL file for compliance and debugging.
Merged from audit.py + audit_log.py to eliminate duplication.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "audit.log")
_lock = Lock()


def _write(entry: dict[str, Any]) -> None:
    try:
        with _lock, open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)


def log_action(
    action: str | int | None = None,
    actor: str | int | None = None,
    resource: str | None = None,
    details: dict[str, Any] | None = None,
    *,
    actor_id: int | None = None,
    resource_id: int | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit event to the JSONL log file.

    Supports both calling conventions:
    - log_action(action, actor=..., resource=..., details=...)
    - log_action(actor_id, action, resource, resource_id=..., ip_address=...)
    - log_action(actor_id=..., action=..., resource=..., resource_id=..., ip_address=...)
    """
    if actor_id is not None:
        _write(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "actor_id": actor_id,
                "action": action if isinstance(action, str) else "unknown",
                "resource": resource or "unknown",
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
            }
        )
    elif isinstance(action, int):
        _write(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "actor_id": action,
                "action": actor if isinstance(actor, str) else "unknown",
                "resource": resource or "unknown",
                "resource_id": resource_id,
                "details": details or {},
                "ip_address": ip_address,
            }
        )
    else:
        _write(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "actor": actor,
                "resource": resource,
                "details": details or {},
            }
        )


def read_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Read the last ``limit`` audit events from the JSONL log file.

    The file is scanned entirely and the lines are **reversed**
    so that it returns the most recent events first; the rows
    unparsable (corrupted JSON) are skipped without interrupting reading.
    """
    path = Path(AUDIT_LOG_PATH)
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
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
