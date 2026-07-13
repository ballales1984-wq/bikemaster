"""Domain event bus for BikeMaster.

Provides a simple publish-subscribe mechanism for domain events.
Events: RideCreated, AthleteUpdated, BadgeEarned, TrainingGenerated.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

STRICT_MODE = os.getenv("EVENT_BUS_STRICT_MODE", "false").lower() in ("true", "1", "yes")

_handler_cache: dict[str, list[Callable[..., Any]]] = defaultdict(list)
_event_bus_running: bool = False


def subscribe(event_type: str, handler: Callable[..., Any]) -> None:
    """Register a handler for an event type."""
    _handler_cache[event_type].append(handler)


async def publish(event_type: str, data: dict[str, Any] | None = None) -> None:
    """Publish an event to all registered handlers."""
    for handler in _handler_cache[event_type]:
        try:
            await handler(data or {})
        except Exception as exc:
            if STRICT_MODE:
                logger.error("Event handler failed for %s: %s", event_type, exc, exc_info=True)
                raise
            logger.error("Event handler failed for %s", event_type, exc_info=True)


def clear_handlers() -> None:
    """Clear all handlers (useful for testing)."""
    _handler_cache.clear()


def is_event_bus_running() -> bool:
    """Return whether the event bus lifecycle has been started."""
    return _event_bus_running


async def start_event_bus() -> None:
    """Start the event bus lifecycle (idempotent).

    The bus is an in-memory pub/sub registry; starting it simply marks the
    lifecycle as active so it can be managed centrally in the application
    lifespan and surfaced in health checks.
    """
    global _event_bus_running
    if _event_bus_running:
        return
    _event_bus_running = True
    logger.info("Domain event bus started")


async def stop_event_bus() -> None:
    """Stop the event bus lifecycle (idempotent)."""
    global _event_bus_running
    if not _event_bus_running:
        return
    _event_bus_running = False
    logger.info("Domain event bus stopped")


# Domain events
class RideCreated:
    type = "ride.created"


class AthleteUpdated:
    type = "athlete.updated"


class BadgeEarned:
    type = "badge.earned"


class TrainingGenerated:
    type = "training.generated"
