"""Simple audit log for admin actions.

Writes audit entries to a JSONL file for compliance and debugging.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
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
    action: str,
    actor: str | None = None,
    resource: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    _write(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "details": details or {},
        }
    )
