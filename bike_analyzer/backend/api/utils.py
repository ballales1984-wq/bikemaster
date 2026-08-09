"""Shared utilities for API routes and app factory."""

from ipaddress import AddressValueError, ip_address, ip_network

from fastapi import Request

_TRUSTED_PROXIES: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.1",
    "::1",
)


def _forwarded_value(header_value: str | None) -> str:
    """Estrae il primo valore dall'header X-Forwarded-For (split su virgola)."""
    if not header_value:
        return ""
    first = header_value.split(",", 1)[0].strip()
    try:
        ip_address(first)
    except (AddressValueError, ValueError):
        return ""
    return first


_TRUSTED_TEST_CLIENT_HOST = "testclient"


def _is_trusted_proxy(ip_str: str) -> bool:
    """Verifica se l'IP appartiene a una rete trusted (private loopback)."""
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


def _trusted_forwarded_value(request: Request, header_name: str) -> str:
    """Return the first forwarded value only when the immediate client is a trusted proxy.

    Prevents header spoofing (open redirect / IP spoofing) when the app is reached directly.
    """
    client_host = request.client.host if request.client else ""
    if not _is_trusted_proxy(client_host):
        return ""
    return _forwarded_value(request.headers.get(header_name))
