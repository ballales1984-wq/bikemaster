"""Tests for the domain event bus."""

import pytest

from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
    clear_handlers,
    publish,
    subscribe,
)


@pytest.fixture(autouse=True)
def cleanup():
    clear_handlers()
    yield
    clear_handlers()


def test_subscribe_and_publish_sync_handler():
    received = []

    def handler(data):
        received.append(data)

    subscribe("test.event", handler)
    import asyncio

    asyncio.run(publish("test.event", {"key": "value"}))
    assert len(received) == 1
    assert received[0] == {"key": "value"}


def test_publish_no_data_default():
    received = []

    def handler(data):
        received.append(data)

    subscribe("test.event2", handler)
    import asyncio

    asyncio.run(publish("test.event2"))
    assert len(received) == 1
    assert received[0] == {}


def test_publish_multiple_handlers():
    results = []

    def handler_a(data):
        results.append(("a", data))

    def handler_b(data):
        results.append(("b", data))

    subscribe("multi.event", handler_a)
    subscribe("multi.event", handler_b)
    import asyncio

    asyncio.run(publish("multi.event", {"x": 1}))
    assert len(results) == 2
    assert ("a", {"x": 1}) in results
    assert ("b", {"x": 1}) in results


def test_publish_strict_mode_raises(monkeypatch):
    import bike_analyzer.backend.events as events_mod

    monkeypatch.setattr(events_mod, "STRICT_MODE", True)

    def bad_handler(data):
        raise RuntimeError("handler error")

    subscribe("strict.event", bad_handler)
    import asyncio

    with pytest.raises(RuntimeError, match="handler error"):
        asyncio.run(publish("strict.event"))


def test_publish_non_strict_logs_error():
    import os

    os.environ["EVENT_BUS_STRICT_MODE"] = "false"
    try:
        def bad_handler(data):
            raise RuntimeError("handler error")

        subscribe("nostrict.event", bad_handler)
        import asyncio

        asyncio.run(publish("nostrict.event"))
    finally:
        os.environ.pop("EVENT_BUS_STRICT_MODE", None)


def test_clear_handlers():
    calls = []

    def handler(data):
        calls.append(data)

    subscribe("clear.event", handler)
    clear_handlers()
    import asyncio

    asyncio.run(publish("clear.event"))
    assert len(calls) == 0


def test_domain_event_types():
    assert RideCreated.type == "ride.created"
    assert AthleteUpdated.type == "athlete.updated"
    assert BadgeEarned.type == "badge.earned"
    assert TrainingGenerated.type == "training.generated"


def test_publish_skips_unregistered_event():
    import asyncio

    result = asyncio.run(publish("nonexistent.event.type"))
    assert result is None
