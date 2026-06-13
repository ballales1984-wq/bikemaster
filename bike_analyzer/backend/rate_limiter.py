"""Shared rate limiter for slowapi."""

import logging
from ipaddress import AddressValueError, ip_address

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

_TRUSTED_PROXIES: tuple[str, ...] = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.1",
    "::1",
)


def _is_trusted_proxy(ip_str: str) -> bool:
    try:
        addr = ip_address(ip_str)
        for prefix in _TRUSTED_PROXIES:
            if addr in ip_address(prefix):
                return True
    except (AddressValueError, ValueError):
        pass
    return False


def get_limiter_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        client_host = request.client.host if request.client else "unknown"
        if _is_trusted_proxy(client_host):
            return first_hop
        logger.debug("X-Forwarded-For from untrusted source %s, using direct IP", client_host)
    return get_remote_address(request)


limiter = Limiter(key_func=get_limiter_key)
