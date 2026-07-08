"""Minimal async DB adapter for tests/legacy imports."""

from __future__ import annotations

from typing import Any


async def get_rides_by_athlete_async(*args: Any, **kwargs: Any) -> list[dict]:
    return []
