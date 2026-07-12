"""Logger helper.

The single source of logging configuration is :mod:`bike_analyzer.backend.logging_config`
(structured JSON formatter + correlation id). This module keeps the ``get_logger``
and ``setup_logging`` entry points used across the codebase but delegates to it so
there is exactly one logging configuration in the project.
"""

from __future__ import annotations

from logging import Logger, getLogger

from ..logging_config import REQUEST_ID_CONTEXT, setup_logging

__all__ = ["get_logger", "setup_logging", "REQUEST_ID_CONTEXT"]


def get_logger(name: str) -> Logger:
    """Return a module-level logger for ``name``."""
    return getLogger(name)
