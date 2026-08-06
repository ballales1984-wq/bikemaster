"""Integration tests for the Athlete State Engine API endpoints."""

from __future__ import annotations

import asyncio
import datetime as dt
import os

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.slow

from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token


def _make_athlete_client(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_path
    db_mod.DB_PATH = db_path
    db_mod.init_db()
    athlete_id = db_mod.save_athlete({"name": "Test Rider", "experience_level": "Intermediate"})
    db_mod.update_athlete(athlete_id, {"tenant_id": athlete_id})
    token = create_access_token(subject=str(athlete_id), is_admin=False, tenant_id=athlete_id)
    tc = TestClient(create_app())
    tc.headers["Authorization"] = f"Bearer {token}"
    return tc, athlete_id


def test_athlete_state_endpoint_with_auth(tmp_path):
    tc, athlete_id = _make_athlete_client(tmp_path)
    resp = tc.get("/api/v1/athlete/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["athlete_id"] == athlete_id
    assert "readiness" in data
    assert "fatigue_score" in data
    assert "ctl" in data
    assert "atl" in data
    assert "tsb" in data
    assert "risk_level" in data
    assert data["risk_level"] in ("ok", "warning", "high", "block")


def test_athlete_state_in_workout_generation(tmp_path):
    tc, athlete_id = _make_athlete_client(tmp_path)
    try:
        resp = tc.post("/api/v1/training/workouts/generate", json={"goal_id": 1, "event_count": 4})
    except RuntimeError as e:
        if "SQLAlchemy" in str(e):
            pytest.skip("SQLAlchemy/PostgreSQL not configured in test environment")
        raise
    assert resp.status_code in (200, 404, 422)
    if resp.status_code == 200:
        data = resp.json()
        assert "athlete_state" in data
        assert "generated" in data
        assert data["athlete_state"]["athlete_id"] == athlete_id


def test_athlete_state_model_roundtrip():
    from datetime import datetime

    from bike_analyzer.backend.analytics.athlete_state.models import AthleteState

    state = AthleteState(
        athlete_id=1,
        computed_at=datetime(2024, 6, 15, 10, 0, 0),
        fatigue_score=5.0,
        readiness=80.0,
        acwr=1.2,
        tsb=6.0,
        atl=70.0,
        ctl=75.0,
        fitness=75.0,
        fatigue=70.0,
        form=6.0,
        recovery_hours_needed=16.0,
        weekly_tss=500.0,
        monthly_tss=2000.0,
        trend_7d="increasing",
        trend_30d="stable",
        risk_indicators=["high_fatigue"],
        recommendation="Ready for hard effort",
        risk_level="ok",
    )
    d = state.to_dict()
    assert d["athlete_id"] == 1
    assert d["fatigue_score"] == 5.0
    assert d["readiness"] == 80.0
    assert d["is_ready_for_hard_effort"] is True

    dc = state.to_dataclass()
    assert dc.fatigue_score == 5.0
    assert dc.readiness == 80.0
    assert dc.acwr == 1.2


def test_e2e_import_ride_then_state_plan_adapt_notify(tmp_path):
    """End-to-end scenario (step 5):

    import ride -> compute athlete state -> generate plan (fatigue adjusted)
    -> simulate adaptation event -> verify proactive notifications fire.
    """
    from bike_analyzer.backend.analytics.adaptation_engine import (
        AdaptationEngine,
    )
    from bike_analyzer.backend.analytics.adaptation_rules import (
        AthleteState as AdaAthleteState,
    )
    from bike_analyzer.backend.analytics.adaptation_rules import (
        WorkoutPlan,
    )
    from bike_analyzer.backend.analytics.athlete_state.service import AthleteStateService
    from bike_analyzer.backend.analytics.proactive import (
        ContextEvaluator,
        NotificationCategory,
        NotificationContext,
    )
    from bike_analyzer.backend.analytics.training.models import (
        GoalType,
        PlanConstraints,
        TrainingGoal,
    )
    from bike_analyzer.backend.analytics.training.workout_generator import WorkoutGenerator
    from bike_analyzer.backend.models.models import Ride

    tc, athlete_id = _make_athlete_client(tmp_path)

    # 1. Import a ride (persisted to the SQLite store).
    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    db_mod.save_ride(
        {
            "athlete_id": athlete_id,
            "tenant_id": athlete_id,
            "date": today,
            "duration_minutes": 180,
            "distance_km": 90.0,
            "avg_speed_kmh": 30.0,
            "heart_rate_avg": 170.0,
            "elevation_gain_m": 2000.0,
            "weight_kg": 70.0,
        }
    )

    # 2. Compute athlete state via the HTTP endpoint.
    resp = tc.get("/api/v1/athlete/state")
    assert resp.status_code == 200
    state_data = resp.json()
    assert state_data["athlete_id"] == athlete_id
    assert state_data["weekly_tss"] > 0
    assert state_data["fatigue_score"] > 0

    # 3. Generate a training week using the computed fatigue.
    service = AthleteStateService(ftp=250.0)
    state = asyncio.run(service.calculate_current_state(
        athlete_id=athlete_id,
        rides=[Ride(**r) for r in db_mod.get_rides_by_athlete(athlete_id)],
    ))
    goal = TrainingGoal(goal_type=GoalType.MAINTENANCE, description="base")
    constraints = PlanConstraints(days_per_week=4, hours_per_session=1.5)
    gen = WorkoutGenerator(athlete=None, ftp=250.0)
    workouts = gen.generate_for_week(
        goal=goal,
        constraints=constraints,
        start_date=dt.datetime.now(),
        fitness_tss=state.weekly_tss,
        fatigue_score=state.fatigue_score,
    )
    assert len(workouts) == 4
    assert workouts[0].duration_minutes > 0

    # 4. Simulate a skipped-ride adaptation event using the athlete state.
    planned = [
        WorkoutPlan(date=today, workout_type="endurance", distance_km=30,
                    duration_minutes=60, intensity_factor=0.7, title="E"),
        WorkoutPlan(date=today, workout_type="threshold", distance_km=40,
                    duration_minutes=80, intensity_factor=0.9, title="T"),
        WorkoutPlan(date=today, workout_type="recovery", distance_km=20,
                    duration_minutes=40, intensity_factor=0.55, title="R"),
    ]
    ada_state = AdaAthleteState(
        fatigue_score=state.fatigue_score,
        readiness=state.readiness,
        acwr=state.acwr,
        tsb=state.tsb,
        atl=state.atl,
        ctl=state.ctl,
    )
    plan = AdaptationEngine().adapt_skipped_ride(planned, 0, ada_state)
    adapted = plan.to_dict()
    assert adapted["strategy"]
    assert len(adapted["adapted_plan"]) == len(planned)

    # 5. Verify the proactive assistant fires a recovery notification when
    #    the athlete state shows insufficient recovery (negative TSB).
    context = NotificationContext(
        athlete_state={"tsb": state.tsb, "fatigue_score": state.fatigue_score},
        plan={"planned_today": True},
    )
    score = ContextEvaluator.evaluate(
        context,
        category=NotificationCategory.RECOVERY.value,
        signals={"insufficient_recovery": state.tsb < -15},
    )
    if state.tsb < -15:
        assert score.should_notify is True
    else:
        assert 1 <= score.urgency <= 5


__all__ = [
    "test_athlete_state_endpoint_with_auth",
    "test_athlete_state_in_workout_generation",
    "test_athlete_state_model_roundtrip",
    "test_e2e_import_ride_then_state_plan_adapt_notify",
]
