"""Training API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from ...models.models import Ride
from ...security import get_current_user
from ..routes import _current_athlete_id, _ensure_athlete_access
from ...analytics.repositories.ride_repository import RideRepository
from ...analytics.repositories.training_goal_repository import TrainingGoalRepository
from ...analytics.training_load import (
    calculate_atl_ctl_tsb,
    get_7day_fitness_summary,
    get_current_training_status,
)

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/load")
async def get_training_load(
    athlete_id: int = Query(...),
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Return ATL/CTL/TSB training load metrics for the last N days."""
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in await RideRepository().list_all(athlete_id=athlete_id)]
    loads = await asyncio.to_thread(calculate_atl_ctl_tsb, rides)
    recent = loads[-days:] if len(loads) > days else loads
    return {"athlete_id": athlete_id, "days": days, "training_loads": list(recent)}


@router.get("/status")
async def get_training_status(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Return current fitness status with ATL/CTL/TSB-based recommendation."""
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in await RideRepository().list_all(athlete_id=athlete_id)]
    status = await asyncio.to_thread(get_current_training_status, rides)
    return {"athlete_id": athlete_id, **status}


@router.get("/summary")
async def get_7day_summary(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Return a 7-day fitness summary for the dashboard."""
    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in await RideRepository().list_all(athlete_id=athlete_id)]
    summary = await asyncio.to_thread(get_7day_fitness_summary, rides)
    return {"athlete_id": athlete_id, "summary": summary}


@router.post("/goals")
async def create_training_goal(goal_data: dict, current_user: dict = Depends(get_current_user)):
    """Create a training goal for an athlete (requires PostgreSQL)."""
    if not TrainingGoalRepository.is_sqlalchemy_available():
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    goal_athlete_id = goal_data.get("athlete_id") or current_user["id"]
    _ensure_athlete_access(goal_athlete_id, current_user)
    goal = {
        "athlete_id": goal_athlete_id,
        "title": goal_data.get("title", ""),
        "description": goal_data.get("description"),
        "goal_type": goal_data.get("goal_type", "granfondo"),
        "target_date": goal_data.get("target_date"),
        "target_distance_km": goal_data.get("target_distance_km"),
        "target_elevation_m": goal_data.get("target_elevation_m"),
        "status": "active",
    }
    goal_id = TrainingGoalRepository.save_training_goal(goal["athlete_id"], goal)
    return {"id": goal_id, **goal}


@router.get("/goals")
async def list_training_goals(
    athlete_id: int = Query(...),
    status: str = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List training goals for athlete."""
    if not TrainingGoalRepository.is_sqlalchemy_available():
        raise HTTPException(status_code=500, detail="SQLAlchemy not available")
    _ensure_athlete_access(athlete_id, current_user)
    goals = TrainingGoalRepository.get_training_goals(athlete_id, status)
    return {"goals": goals}


@router.post("/workouts/generate")
async def generate_workouts(
    goal_id: int = Body(...),
    event_count: int = Body(12, ge=4, le=20),
    current_user: dict = Depends(get_current_user),
):
    """Generate planned workouts for a granfondo goal."""
    from ...analytics.training_load import get_current_training_status
    from ...analytics.repositories.ride_repository import RideRepository
    from ...analytics.repositories.training_goal_repository import TrainingGoalRepository
    from ...analytics.athlete_state.service import AthleteStateService
    from ...analytics.training.models import PlanConstraints, TrainingGoal
    from ...analytics.training.workout_generator import WorkoutGenerator

    with TrainingGoalRepository.get_session() as session:
        goal = session.query(TrainingGoalRepository.get_training_goal_model()).filter(TrainingGoalRepository.get_training_goal_model().id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        if goal.athlete_id is None:
            raise HTTPException(status_code=422, detail="Goal has no associated athlete")
        _ensure_athlete_access(goal.athlete_id, current_user)

    rides = [Ride(**r) for r in await RideRepository().list_all(athlete_id=goal.athlete_id)]
    get_current_training_status(rides) if rides else {"ctl": 0}

    athlete_state_service = AthleteStateService()
    athlete_state = await athlete_state_service.calculate_current_state(
        athlete_id=goal.athlete_id,
        rides=rides,
    )

    from datetime import datetime as dt

    goal_type_map = {
        "granfondo": "granfondo",
        "race": "race",
        "fitness": "maintenance",
        "fondo": "granfondo",
        "custom": "maintenance",
    }
    goal_type_str = goal_type_map.get(goal.goal_type, "maintenance")
    try:
        goal_enum = __import__("bike_analyzer.backend.analytics.training.models", fromlist=["GoalType"]).GoalType(goal_type_str)
    except Exception:
        goal_enum = __import__("bike_analyzer.backend.analytics.training.models", fromlist=["GoalType"]).GoalType.MAINTENANCE

    training_goal = TrainingGoal(
        goal_type=goal_enum,
        target_date=goal.target_date,
        target_distance_km=goal.target_distance_km,
        description=goal.description or "",
    )
    constraints = PlanConstraints(days_per_week=4, hours_per_session=1.5)

    generator = WorkoutGenerator(athlete=None, ftp=250.0)
    workouts = generator.generate_for_week(
        goal=training_goal,
        constraints=constraints,
        start_date=dt.now(),
        fitness_tss=athlete_state.weekly_tss,
        fatigue_score=athlete_state.fatigue_score,
    )

    return {
        "generated": len(workouts),
        "goal_id": goal_id,
        "athlete_state": athlete_state.to_dict(),
    }
