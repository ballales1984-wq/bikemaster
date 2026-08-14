"""Shared trusted proxy utilities.

Consolidates duplicated trusted proxy logic from:
- bike_analyzer/backend/rate_limiter.py
- bike_analyzer/backend/api/utils.py
- bike_analyzer/backend/hub/routes.py
"""

from __future__ import annotations

from ipaddress import AddressValueError, ip_address, ip_network

from fastapi import Request

_TRUSTED_PROXIES: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.1",
    "::1",
)

_TRUSTED_TEST_CLIENT_HOST = "testclient"


def _is_trusted_proxy(ip_str: str) -> bool:
    """Verify if the IP belongs to a trusted network (private, loopback)."""
    if ip_str == _TRUSTED_TEST_CLIENT_HOST:
        return True
    try:
        addr = ip_address(ip_str)
    except (AddressValueError, ValueError):
        return False
    for prefix in _TRUSTED_PROXIES:
        try:
            if addr in ip_network(prefix):
                return True
        except (AddressValueError, ValueError):
            if addr == ip_address(prefix):
                return True
    return False


def forwarded_value(header_value: str | None) -> str:
    """Extract the first value from an X-Forwarded-For header (split on comma)."""
    if not header_value:
        return ""
    first = header_value.split(",", 1)[0].strip()
    try:
        ip_address(first)
    except (AddressValueError, ValueError):
        return ""
    return first


def trusted_forwarded_value(request: Request, header_name: str) -> str:
    """Return the first forwarded value only when the immediate client is a trusted proxy.

    Prevents header spoofing (open redirect / IP spoofing) when the app is reached directly.
    """
    client_host = request.client.host if request.client else ""
    if not _is_trusted_proxy(client_host):
        return ""
    return forwarded_value(request.headers.get(header_name))


is_trusted_proxy = _is_trusted_proxy
