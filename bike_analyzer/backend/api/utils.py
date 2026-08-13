"""Shared utilities for API routes and app factory."""

from bike_analyzer.backend.trusted_proxies import (
    _is_trusted_proxy as _is_trusted_proxy,
    forwarded_value as _forwarded_value,
    trusted_forwarded_value as _trusted_forwarded_value,
)
