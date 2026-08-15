"""Shared utilities for API routes and app factory."""

from bike_analyzer.backend.trusted_proxies import (  # noqa: F401
    _is_trusted_proxy as _is_trusted_proxy,
)
from bike_analyzer.backend.trusted_proxies import (
    forwarded_value as _forwarded_value,
)
from bike_analyzer.backend.trusted_proxies import (
    trusted_forwarded_value as _trusted_forwarded_value,
)

__all__ = ["_is_trusted_proxy", "_forwarded_value", "_trusted_forwarded_value"]
