"""Shared rate limiter for slowapi."""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_proxy_aware_address(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For when behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_proxy_aware_address)
