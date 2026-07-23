"""Tests for backend.api.adaptation_routes."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from bike_analyzer.backend.analytics.adaptation_schemas import (
    AdaptationRequest,
    AdaptationResponse,
    EventType,
    WorkoutPlanItem,
)
from bike_analyzer.backend.analytics.adaptation_engine import (
    AdaptationEngine,
    AthleteState,
    WorkoutPlan,
)
from bike_analyzer.backend.api.adaptation_routes import (
    _to_response,
    _to_workout_plan,
    adapt_plan,
)


def _make_item(**overrides):
    base = {
        "date": "2025-01-15",
        "workout_type": "endurance",
        "distance_km": 40.0,
        "duration_minutes": 120,
        "intensity_factor": 0.7,
        "title": "Endurance Ride",
        "description": "Steady base ride",
        "is_recovery": False,
        "locked": False,
    }
    base.update(overrides)
    return WorkoutPlanItem(**base)


def _make_request(**overrides):
    base = {
        "planned": [_make_item()],
        "event_type": EventType.SKIPPED_RIDE,
        "skipped_index": 0,
        "athlete_state": {
            "fatigue_score": 0.3,
            "readiness": 80.0,
            "acwr": 0.9,
            "tsb": 10.0,
            "atl": 45.0,
            "ctl": 80.0,
        },
        "current_acute_load": 50.0,
        "from_index": 0,
        "actual_km": None,
        "actual_minutes": None,
    }
    base.update(overrides)
    return AdaptationRequest(**base)


class TestToWorkoutPlan:
    def test_empty_list(self):
        result = _to_workout_plan([])
        assert result == []

    def test_single_item(self):
        items = [_make_item()]
        result = _to_workout_plan(items)
        assert len(result) == 1
        assert result[0].date == "2025-01-15"
        assert result[0].title == "Endurance Ride"

    def test_multiple_items(self):
        items = [
            _make_item(title="Ride 1"),
            _make_item(title="Ride 2", distance_km=60.0),
        ]
        result = _to_workout_plan(items)
        assert len(result) == 2
        assert result[0].title == "Ride 1"
        assert result[1].distance_km == 60.0


class TestAdaptPlanErrors:
    def test_empty_planned_raises(self):
        req = _make_request(planned=[])
        with pytest.raises(HTTPException) as exc_info:
            adapt_plan(req)
        assert exc_info.value.status_code == 400

    def test_negative_skipped_index_raises(self):
        req = _make_request(skipped_index=-1)
        with pytest.raises(HTTPException) as exc_info:
            adapt_plan(req)
        assert exc_info.value.status_code == 400

    def test_skipped_index_out_of_range_raises(self):
        req = _make_request(skipped_index=5)
        with pytest.raises(HTTPException) as exc_info:
            adapt_plan(req)
        assert exc_info.value.status_code == 400


class TestAdaptPlanBranches:
    def test_skipped_ride(self):
        req = _make_request(event_type=EventType.SKIPPED_RIDE)
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_longer_ride_with_actual_values(self):
        req = _make_request(
            event_type=EventType.LONGER_RIDE,
            actual_km=80.0,
            actual_minutes=180,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_longer_ride_falls_back_to_planned(self):
        req = _make_request(
            event_type=EventType.LONGER_RIDE,
            actual_km=None,
            actual_minutes=None,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_low_recovery(self):
        req = _make_request(
            event_type=EventType.LOW_RECOVERY,
            from_index=1,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_goal_change(self):
        req = _make_request(
            event_type=EventType.GOAL_CHANGE,
            from_index=1,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_bad_weather(self):
        req = _make_request(
            event_type=EventType.BAD_WEATHER,
            from_index=0,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_calendar_block(self):
        req = _make_request(
            event_type=EventType.CALENDAR_BLOCK,
            from_index=0,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)

    def test_partial_ride(self):
        req = _make_request(
            event_type=EventType.PARTIAL_RIDE,
            skipped_index=0,
            actual_km=15.0,
            actual_minutes=45,
        )
        result = adapt_plan(req)
        assert isinstance(result, AdaptationResponse)


from starlette.testclient import TestClient


class TestAdaptationRoutesEndpoint:
    def test_post_adapt_endpoint(self):
        from bike_analyzer.backend.api.app_factory import create_app
        app = create_app()
        client = TestClient(app)
        payload = {
            "planned": [
                {
                    "date": "2025-01-15",
                    "workout_type": "endurance",
                    "distance_km": 40.0,
                    "duration_minutes": 120,
                    "intensity_factor": 0.7,
                    "title": "Endurance Ride",
                    "description": "Steady base ride",
                    "is_recovery": False,
                    "locked": False,
                }
            ],
            "event_type": "skipped_ride",
            "skipped_index": 0,
            "athlete_state": {
                "fatigue_score": 0.3,
                "readiness": 80.0,
                "acwr": 0.9,
                "tsb": 10.0,
                "atl": 45.0,
                "ctl": 80.0,
            },
            "current_acute_load": 50.0,
            "from_index": 0,
            "actual_km": None,
            "actual_minutes": None,
        }
        response = client.post("/api/v1/training/plan/adapt", json=payload)
        assert response.status_code == 200

    def test_post_adapt_empty_planned_returns_400(self):
        from bike_analyzer.backend.api.app_factory import create_app
        app = create_app()
        client = TestClient(app)
        payload = {
            "planned": [],
            "event_type": "skipped_ride",
            "skipped_index": 0,
            "athlete_state": {
                "fatigue_score": 0.3,
                "readiness": 80.0,
                "acwr": 0.9,
                "tsb": 10.0,
                "atl": 45.0,
                "ctl": 80.0,
            },
            "current_acute_load": 50.0,
            "from_index": 0,
        }
        response = client.post("/api/v1/training/plan/adapt", json=payload)
        assert response.status_code == 400
