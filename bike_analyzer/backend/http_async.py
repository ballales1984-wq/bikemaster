"""Shared async HTTP helpers for BikeMaster integrations.

Provides :func:`request_json`, an ``httpx.AsyncClient`` based wrapper with
exponential backoff on transient failures (429/5xx and transport errors). This
replaces the blocking ``requests`` calls that previously ran inside the event
loop of async FastAPI routes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20.0
MAX_RETRIES = 3
_BACKOFF_BASE = 0.5

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _is_retryable(status: int) -> bool:
    return status in _RETRYABLE_STATUS


async def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """Perform an HTTP request and return the parsed JSON body.

    Retries on transient failures (429/5xx and transport errors) with
    exponential backoff. Raises ``httpx.HTTPStatusError`` for non-2xx
    responses and ``httpx.TransportError`` for connection problems.
    """
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method, url, params=params, data=data, json=json, headers=headers
                )
            if _is_retryable(resp.status_code):
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(_BACKOFF_BASE * (2**attempt))
                    continue
                resp.raise_for_status()
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return resp.text
        except (httpx.TransportError, asyncio.TimeoutError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                await asyncio.sleep(_BACKOFF_BASE * (2**attempt))
                continue
            raise
    # Only reached if every attempt failed; surface the last error.
    assert last_exc is not None
    raise last_exc
