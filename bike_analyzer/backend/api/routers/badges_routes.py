"""Badges API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...analytics.badges import calculate_badges
from ...analytics.repositories.athlete_repository import AthleteRepository
from ...analytics.repositories.ride_repository import RideRepository
from ...security import get_current_user
from ..routes import _ensure_athlete_access

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("/")
async def get_badges(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Get badge achievements for an athlete."""
    from ...events import BadgeEarned, publish

    _ensure_athlete_access(athlete_id, current_user)
    rides = await RideRepository().list_all(athlete_id=athlete_id)
    athlete = await AthleteRepository().get_by_id(athlete_id)
    badges = calculate_badges(athlete_id, list(rides), athlete or {})
    achieved_count = sum(1 for b in badges if b["achieved"])

    for badge in badges:
        if badge.get("achieved"):
            await publish(
                BadgeEarned.type,
                {
                    "athlete_id": athlete_id,
                    "badge_id": badge.get("id"),
                    "badge_name": badge.get("name"),
                },
            )
    return {
        "athlete_id": athlete_id,
        "badges": badges,
        "total_badges": len(badges),
        "achieved": achieved_count,
    }
