"""Lightweight JSONL-backed per-user conversation memory for the AI Coach."""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONVERSATION_LOG_PATH = Path("logs/conversations.jsonl")
_DEFAULT_MAX_TURNS = 50


def _ensure_log_dir() -> None:
    with contextlib.suppress(Exception):
        _CONVERSATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load(user_id: int | str) -> list[dict[str, Any]]:
    """Load conversation messages for a user, ordered oldest-first."""
    uid = str(user_id)
    if not _CONVERSATION_LOG_PATH.exists():
        return []
    messages: list[dict[str, Any]] = []
    try:
        with _CONVERSATION_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("user_id") == uid:
                        messages.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.debug("Conversation store read failed: %s", exc)
    return messages


def append(user_id: int | str, message: dict[str, Any]) -> None:
    """Append a message to the user's conversation history."""
    _ensure_log_dir()
    entry = {
        "user_id": str(user_id),
        "timestamp": datetime.now(UTC).isoformat(),
        "role": message.get("role", "user"),
        "content": message.get("content", ""),
    }
    for key in ("created_at",):
        if key in message:
            entry[key] = message[key]
    try:
        with _CONVERSATION_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("Conversation store write failed: %s", exc)


def prune(user_id: int | str, max_len: int = _DEFAULT_MAX_TURNS) -> int:
    """Keep only the most recent ``max_len`` messages for the user.

    Returns the number of messages removed.
    """
    if max_len <= 0:
        return 0
    uid = str(user_id)
    if not _CONVERSATION_LOG_PATH.exists():
        return 0
    kept: list[str] = []
    user_lines: list[str] = []
    try:
        with _CONVERSATION_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.rstrip("\n")
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                    if entry.get("user_id") == uid:
                        user_lines.append(stripped)
                    else:
                        kept.append(stripped)
                except json.JSONDecodeError:
                    kept.append(stripped)
    except Exception as exc:
        logger.debug("Conversation store prune read failed: %s", exc)
        return 0
    excess = len(user_lines) - max_len
    if excess <= 0:
        return 0
    kept.extend(user_lines[excess:])
    try:
        with _CONVERSATION_LOG_PATH.open("w", encoding="utf-8") as f:
            for line in kept:
                f.write(line + "\n")
    except Exception as exc:
        logger.debug("Conversation store prune write failed: %s", exc)
        return 0
    return excess
