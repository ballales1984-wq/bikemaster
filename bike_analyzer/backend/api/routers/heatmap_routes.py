"""Heatmap API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...analytics.badges import get_heatmap_points
from ...models.models import Ride
from ..routes import _current_athlete_id, get_current_user

router = APIRouter(tags=["heatmap"])


@router.get("/heatmap")
async def get_heatmap(
    athlete_id: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Return heatmap points for the current athlete."""
    target_athlete_id = _current_athlete_id(current_user) if athlete_id is None else athlete_id
    rides = _get_athlete_rides(target_athlete_id, current_user)
    points = _build_heatmap_points(rides)
    return points or {"points": [], "bounds": {}}


def _get_athlete_rides(athlete_id: int, current_user: dict) -> list[Ride]:
    from ...db.database import get_rides_by_athlete

    if not current_user.get("is_admin") and (
        int(athlete_id) != int(current_user.get("athlete_id") or current_user["id"])
    ):
        raise HTTPException(status_code=403, detail="Access denied to this athlete")
    return [Ride(**r) for r in get_rides_by_athlete(athlete_id)]


def _build_heatmap_points(rides: list[Ride]) -> dict:
    ride_dicts = []
    for ride in rides:
        data = ride.__dict__ if hasattr(ride, "__dict__") else {}
        ride_dicts.append(data)
    return get_heatmap_points(ride_dicts)
