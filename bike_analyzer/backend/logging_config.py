"""Structured logging configuration for BikeMaster backend.

Provides:
- JSON formatter with optional correlation/request id
- Module-level logger setup helper
- Safe default config for development/testing
"""

from __future__ import annotations

import contextvars
import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC
from logging.config import DictConfigurator
from typing import Any

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
REQUEST_ID_HEADER = os.getenv("LOG_REQUEST_ID_HEADER", "X-Request-ID")

# Request/correlation id propagated to every log emitted while the context is active
# (HTTP request, background task, ...). Loggers do not need to pass it explicitly.
REQUEST_ID_CONTEXT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


@contextmanager
def request_context(request_id: str | None = None) -> Iterator[str]:
    """Activate a correlation id for the surrounding block of code."""
    import uuid

    rid = request_id or str(uuid.uuid4())
    token = REQUEST_ID_CONTEXT.set(rid)
    try:
        yield rid
    finally:
        REQUEST_ID_CONTEXT.reset(token)


def set_request_id(request_id: str) -> None:
    REQUEST_ID_CONTEXT.set(request_id)


def get_request_id() -> str:
    return REQUEST_ID_CONTEXT.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Prefer an explicit value passed via `extra=`, otherwise fall back to the
        # ambient correlation id (HTTP request / background task context).
        request_id = getattr(record, "request_id", None) or REQUEST_ID_CONTEXT.get()
        record.request_id = request_id
        return True


_STANDARD_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class _JsonFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__()
        self._default_fields = [
            "name",
            "levelname",
            "message",
            "request_id",
            "asctime",
        ]

    def format(self, record: logging.LogRecord) -> str:
        from datetime import datetime

        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            data["stack_info"] = record.stack_info
        # Only surface genuinely custom "extra" fields, not the standard
        # LogRecord attributes (msg, args, pathname, lineno, thread, ...).
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_RECORD_ATTRS
            and k not in self._default_fields
            and not k.startswith("_")
        }
        if extra:
            data["extra"] = extra
        lines = ["{"]
        for k, v in data.items():
            if isinstance(v, str) and any(c in v for c in ["\"", "\n", "{", "}"]):
                v = v.replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'  "{k}": "{v}"')
        lines.append("}")
        return "\n".join(lines)


def _build_config() -> dict[str, Any]:
    formatter = "json" if LOG_FORMAT == "json" else "standard"
    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": formatter,
            "filters": ["request_id"],
        }
    }
    if os.getenv("LOG_FILE"):
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": os.getenv("LOG_FILE"),
            "encoding": "utf-8",
            "formatter": formatter,
            "filters": ["request_id"],
        }
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": f"{_RequestIdFilter.__module__}._RequestIdFilter"},
        },
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(request_id)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {"()": f"{_JsonFormatter.__module__}._JsonFormatter"},
        },
        "handlers": handlers,
        "root": {
            "level": LOG_LEVEL,
            "handlers": list(handlers.keys()),
        },
    }


def setup_logging() -> None:
    config = _build_config()
    try:
        DictConfigurator(config).configure()
    except Exception:
        logging.basicConfig(level=LOG_LEVEL)
        logging.getLogger(__name__).warning(
            "Structured logging config failed, falling back to basicConfig",
            exc_info=True,
        )
