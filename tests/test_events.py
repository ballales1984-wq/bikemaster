"""Tests for event bus module."""

import pytest

from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
    clear_handlers,
    is_event_bus_running,
    publish,
    start_event_bus,
    stop_event_bus,
    subscribe,
)


class TestSubscribePublish:
    def setup_method(self):
        clear_handlers()

    def teardown_method(self):
        clear_handlers()

    def test_subscribe_and_publish(self):
        received = []

        async def handler(data):
            received.append(data)

        subscribe("test.event", handler)
        import asyncio

        asyncio.run(publish("test.event", {"key": "value"}))
        assert len(received) == 1
        assert received[0] == {"key": "value"}

    def test_multiple_handlers(self):
        results = []

        async def h1(data):
            results.append(1)

        async def h2(data):
            results.append(2)

        subscribe("multi", h1)
        subscribe("multi", h2)
        import asyncio

        asyncio.run(publish("multi"))
        assert sorted(results) == [1, 2]

    def test_publish_no_handlers(self):
        import asyncio

        result = asyncio.run(publish("nonexistent.event"))
        assert result is None

    def test_handler_exception_non_strict(self, monkeypatch):
        monkeypatch.setattr("bike_analyzer.backend.events.STRICT_MODE", False)

        async def bad_handler(data):
            raise RuntimeError("oops")

        subscribe("error.test", bad_handler)
        import asyncio

        asyncio.run(publish("error.test"))
        # Should not raise, just log

    def test_handler_exception_strict(self, monkeypatch):
        monkeypatch.setattr("bike_analyzer.backend.events.STRICT_MODE", True)

        async def bad_handler(data):
            raise RuntimeError("oops")

        subscribe("error.strict", bad_handler)
        import asyncio

        with pytest.raises(RuntimeError, match="oops"):
            asyncio.run(publish("error.strict"))

    def test_clear_handlers(self):
        async def h(data):
            pass

        subscribe("test", h)
        clear_handlers()
        import asyncio

        asyncio.run(publish("test"))
        # No handlers should fire without error


class TestDomainEvents:
    def test_ride_created_event(self):
        assert RideCreated.type == "ride.created"

    def test_athlete_updated_event(self):
        assert AthleteUpdated.type == "athlete.updated"

    def test_badge_earned_event(self):
        assert BadgeEarned.type == "badge.earned"

    def test_training_generated_event(self):
        assert TrainingGenerated.type == "training.generated"


class TestEventBusLifecycle:
    def setup_method(self):

        import bike_analyzer.backend.events as ev

        ev._event_bus_running = False

    def test_start_event_bus(self):
        import asyncio

        asyncio.run(start_event_bus())
        assert is_event_bus_running() is True
        asyncio.run(stop_event_bus())

    def test_start_event_bus_idempotent(self):
        import asyncio

        asyncio.run(start_event_bus())
        asyncio.run(start_event_bus())
        assert is_event_bus_running() is True
        asyncio.run(stop_event_bus())

    def test_stop_event_bus(self):
        import asyncio

        asyncio.run(start_event_bus())
        asyncio.run(stop_event_bus())
        assert is_event_bus_running() is False

    def test_stop_event_bus_idempotent(self):
        import asyncio

        asyncio.run(stop_event_bus())
        assert is_event_bus_running() is False

    def test_is_event_bus_running_initial(self):
        assert is_event_bus_running() is False

    def test_publish_after_start(self):
        import asyncio

        received = []

        async def handler(data):
            received.append(data)

        subscribe("lifecycle.test", handler)
        asyncio.run(start_event_bus())
        asyncio.run(publish("lifecycle.test", {"lifecycle": True}))
        assert len(received) == 1
        asyncio.run(stop_event_bus())
        clear_handlers()
