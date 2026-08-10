"""Shared utilities for API routes and app factory."""

from fastapi import Request

from bike_analyzer.backend.trusted_proxies import (
    forwarded_value as _forwarded_value,
)
from bike_analyzer.backend.trusted_proxies import (
    _is_trusted_proxy as _is_trusted_proxy,
)
from bike_analyzer.backend.trusted_proxies import (
    trusted_forwarded_value as _trusted_forwarded_value,
)
