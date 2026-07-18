"""FastAPI routes for dynamic training-plan adaptation.

Exposes ``POST /training/plan/adapt`` which runs the ``AdaptationEngine`` over a
provided plan + athlete state + event and returns an auditable adaptation plan.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ..analytics.adaptation_engine import (
    AdaptationEngine,
    AthleteState,
    WorkoutPlan,
)
from ..analytics.adaptation_schemas import (
    AdaptationRequest,
    AdaptationResponse,
    EventType,
    LoadRedistributionOut,
    WorkoutPlanItem,
)

router = APIRouter(prefix="/training/plan", tags=["adaptation"])


def _to_workout_plan(items: list[WorkoutPlanItem]) -> list[WorkoutPlan]:
    """Converte lista di WorkoutPlanItem (schema) in WorkoutPlan (domain)."""
    return [
        WorkoutPlan(
            date=i.date,
            workout_type=i.workout_type,
            distance_km=i.distance_km,
            duration_minutes=i.duration_minutes,
            intensity_factor=i.intensity_factor,
            title=i.title,
            description=i.description,
            is_recovery=i.is_recovery,
            locked=i.locked,
        )
        for i in items
    ]


def _to_response(plan: Any) -> AdaptationResponse:
    """Converte un AdaptationPlan in AdaptationResponse per l'API."""
    data = plan.to_dict()
    return AdaptationResponse(
        triggered_by=data["triggered_by"],
        strategy=data["strategy"],
        rationale=data["rationale"],
        alerts=data["alerts"],
        redistribution=LoadRedistributionOut(**data["redistribution"]) if data["redistribution"] else None,
        original_plan=[WorkoutPlanItem(**w) for w in data["original_plan"]],
        adapted_plan=[WorkoutPlanItem(**w) for w in data["adapted_plan"]],
        audit=data["audit"],
        generated_at=datetime.now(UTC),
    )


@router.post("/adapt", response_model=AdaptationResponse)
def adapt_plan(req: AdaptationRequest) -> AdaptationResponse:
    """Adapt a training plan to a detected event."""
    if not req.planned:
        raise HTTPException(status_code=400, detail="planned list cannot be empty")
    if req.skipped_index < 0 or req.skipped_index >= len(req.planned):
        raise HTTPException(status_code=400, detail="skipped_index out of range")

    planned = _to_workout_plan(req.planned)
    state = AthleteState(
        fatigue_score=req.athlete_state.fatigue_score,
        readiness=req.athlete_state.readiness,
        acwr=req.athlete_state.acwr,
        tsb=req.athlete_state.tsb,
        atl=req.athlete_state.atl,
        ctl=req.athlete_state.ctl,
    )
    engine = AdaptationEngine()

    etype: EventType = req.event_type
    if etype == EventType.SKIPPED_RIDE:
        plan = engine.adapt_skipped_ride(
            planned, req.skipped_index, state, req.current_acute_load
        )
    elif etype == EventType.LONGER_RIDE:
        plan = engine.adapt_longer_ride(
            planned,
            req.skipped_index,
            req.actual_km or planned[req.skipped_index].distance_km,
            req.actual_minutes or planned[req.skipped_index].duration_minutes,
            state,
        )
    elif etype == EventType.LOW_RECOVERY:
        plan = engine.adapt_low_recovery(planned, state, req.from_index)
    elif etype == EventType.GOAL_CHANGE:
        # Goal change: prefer quality swap to rebalance toward new goal.
        plan = engine.adapt_quality_swap(planned, state, req.from_index)
    else:
        plan = engine.adapt_quality_swap(planned, state, req.from_index)

    return _to_response(plan)
