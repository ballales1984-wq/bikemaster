"""Per-request user-provided API keys.

Each device app can send the user's own external API keys (Groq, Google Maps,
SerpAPI, OpenWeather) via the ``X-User-Api-Keys`` header. The backend uses them
for that request instead of its own server-side keys, so every user brings their
own quota. Keys are scoped to the request via a :class:`~contextvars.ContextVar`
(which is safe under asyncio concurrency) and never persisted server-side.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Known key slots accepted from the client header. Unknown keys are ignored.
USER_KEY_SLOTS = ("groq", "google_maps", "serpapi", "weather", "openweather")

_user_keys: ContextVar[dict[str, str] | None] = ContextVar(
    "user_api_keys", default=None
)


def set_request_user_keys(keys: dict[str, str] | None):
    return _user_keys.set(keys)


def reset_request_user_keys(token: Any) -> None:
    _user_keys.reset(token)


def get_request_user_keys() -> dict[str, str]:
    value = _user_keys.get()
    return value or {}


def parse_user_keys_header(raw: str | None) -> dict[str, str] | None:
    """Parse the ``X-User-Api-Keys`` header (a JSON object of key slots).

    Returns only the known slots with non-empty string values, or ``None`` when
    the header is absent/empty/invalid.
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        data = __import__("json").loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    result: dict[str, str] = {}
    for slot in USER_KEY_SLOTS:
        val = data.get(slot)
        if isinstance(val, str) and val.strip():
            result[slot] = val.strip()
        elif isinstance(val, (int, float)) and slot == "openweather":
            # OpenWeather keys are numeric; normalize to string.
            result[slot] = str(val)
    return result or None
