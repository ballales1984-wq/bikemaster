"""Domain event bus for BikeMaster.

Provides a simple publish-subscribe mechanism for domain events.
Events: RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated.
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from collections.abc import Callable
from typing import Any

_handler_cache: dict[str, list[Callable[..., Any]]] = defaultdict(list)


def subscribe(event_type: str, handler: Callable[..., Any]) -> None:
    """Register a handler for an event type."""
    _handler_cache[event_type].append(handler)


async def publish(event_type: str, data: dict[str, Any] | None = None) -> None:
    """Publish an event to all registered handlers."""
    for handler in _handler_cache[event_type]:
        with contextlib.suppress(Exception):
            await handler(data or {})


def clear_handlers() -> None:
    """Clear all handlers (useful for testing)."""
    _handler_cache.clear()


# Domain events
class RideCreated:
    type = "ride.created"


class AthleteUpdated:
    type = "athlete.updated"


class BadgeEarned:
    type = "badge.earned"


class TrainingGenerated:
    type = "training.generated"
