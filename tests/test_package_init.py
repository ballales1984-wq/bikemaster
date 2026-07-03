"""Tests for package __init__.py lazy-loading modules."""

import pytest

from bike_analyzer.backend.events import (
    AthleteUpdated,
    BadgeEarned,
    RideCreated,
    TrainingGenerated,
)


class TestIngestionPackage:
    def test_getattr_valid(self):
        import bike_analyzer.backend.ingestion as ing_pkg

        func = ing_pkg.parse_fit_file
        assert callable(func)

    def test_getattr_invalid(self):
        import bike_analyzer.backend.ingestion as ing_pkg

        with pytest.raises(AttributeError):
            ing_pkg.nonexistent_function


class TestMapsPackage:
    def test_getattr_valid(self):
        import bike_analyzer.backend.maps as maps_pkg

        func = maps_pkg.create_route_map
        assert callable(func)

    def test_getattr_invalid(self):
        import bike_analyzer.backend.maps as maps_pkg

        with pytest.raises(AttributeError):
            maps_pkg.nonexistent_function


class TestProcessingPackage:
    def test_getattr_valid(self):
        import bike_analyzer.backend.processing as proc_pkg

        func = proc_pkg.build_segments
        assert callable(func)

    def test_getattr_invalid(self):
        import bike_analyzer.backend.processing as proc_pkg

        with pytest.raises(AttributeError):
            proc_pkg.nonexistent_function


class TestTrafficPackage:
    def test_getattr_valid(self):
        import bike_analyzer.backend.traffic as traffic_pkg

        func = traffic_pkg.fetch_incidents
        assert callable(func)

    def test_getattr_invalid(self):
        import bike_analyzer.backend.traffic as traffic_pkg

        with pytest.raises(AttributeError):
            traffic_pkg.nonexistent_function


class TestWeatherPackage:
    def test_getattr_valid(self):
        import bike_analyzer.backend.weather as weather_pkg

        func = weather_pkg.get_weather_for_coordinates
        assert callable(func)

    def test_getattr_invalid(self):
        import bike_analyzer.backend.weather as weather_pkg

        with pytest.raises(AttributeError):
            weather_pkg.nonexistent_function


class TestEventsPackage:
    def test_event_classes(self):
        assert RideCreated.type == "ride.created"
        assert AthleteUpdated.type == "athlete.updated"
        assert BadgeEarned.type == "badge.earned"
        assert TrainingGenerated.type == "training.generated"

    def test_events_subscribe(self):
        import asyncio

        from bike_analyzer.backend.events import (
            clear_handlers,
            publish,
            subscribe,
        )

        received = []

        def handler(data):
            received.append(data)

        subscribe("ride.created", handler)
        asyncio.run(publish("ride.created", {"ride_id": 1}))
        assert len(received) == 1
        assert received[0]["ride_id"] == 1
        clear_handlers()

    def test_clear_handlers(self):
        from bike_analyzer.backend.events import (
            clear_handlers,
            subscribe,
        )

        received = []

        def handler(data):
            received.append(data)

        subscribe("ride.created", handler)
        clear_handlers()
        assert len(received) == 0

    def test_multiple_handlers(self):
        import asyncio

        from bike_analyzer.backend.events import (
            clear_handlers,
            publish,
            subscribe,
        )

        results = []

        def handler_a(data):
            results.append(("a", data))

        def handler_b(data):
            results.append(("b", data))

        subscribe("ride.created", handler_a)
        subscribe("ride.created", handler_b)
        asyncio.run(publish("ride.created", {"ride_id": 2}))
        assert len(results) == 2
        clear_handlers()
