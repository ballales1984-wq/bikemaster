"""Badges API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..routes import _ensure_athlete_access, get_current_user

router = APIRouter(prefix="/badges", tags=["badges"])


@router.get("/")
async def get_badges(athlete_id: int = Query(...), current_user: dict = Depends(get_current_user)):
    """Get badge achievements for an athlete."""
    from ...db.database import get_athlete, get_rides_by_athlete
    from ...models.models import Ride
    from ...events import BadgeEarned, publish

    _ensure_athlete_access(athlete_id, current_user)
    rides = [Ride(**r) for r in get_rides_by_athlete(athlete_id)]
    athlete = get_athlete(athlete_id)
    badges = calculate_badges(athlete_id, [r.to_dict() for r in rides], athlete)
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
