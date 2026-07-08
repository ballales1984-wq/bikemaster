"""Structured logging configuration for BikeMaster backend.

Provides:
- JSON formatter with optional correlation/request id
- Module-level logger setup helper
- Safe default config for development/testing
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from logging.config import DictConfigurator
from typing import Any

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
REQUEST_ID_HEADER = os.getenv("LOG_REQUEST_ID_HEADER", "X-Request-ID")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = getattr(record, "request_id", None) or "-"
        setattr(record, "request_id", request_id)
        return True


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
        from datetime import datetime, timezone

        data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            data["stack_info"] = record.stack_info
        extra = {k: v for k, v in record.__dict__.items() if k not in self._default_fields and not k.startswith("_")}
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
        logging.getLogger(__name__).warning("Structured logging config failed, falling back to basicConfig", exc_info=True)
