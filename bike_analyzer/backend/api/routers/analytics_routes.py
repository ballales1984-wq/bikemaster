"""Analytics API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from ...analytics.repositories.athlete_repository import AthleteRepository
from ...analytics.repositories.ride_repository import RideRepository
from ...models.models import AthleteProfile, Ride
from ..routes import _current_athlete_id, _get_athlete_rides, get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/speed-data")
async def speed_analytics(limit: int = Query(10, ge=1, le=50), current_user: dict = Depends(get_current_user)):
    """Return recent ride speed data for charting."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = await RideRepository().list_all(athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id)
    recent = rides[-limit:] if len(rides) > limit else rides
    return {
        "labels": [r.get("date", "Ride")[-10:] if r.get("date") else "Ride" for r in recent],
        "speeds": [r.get("avg_speed_kmh", 0) for r in recent],
        "distances": [r.get("distance_km", 0) for r in recent],
    }


@router.get("/trends")
async def get_fitness_trends(
    metric: str = Query("distance_km"),
    window: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Get fitness trend analysis for athlete's rides."""
    from ...analytics.analytics_trends import calculate_fitness_trends

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [
        Ride(**r)
        for r in await RideRepository().list_all(
            athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id
        )
    ]
    return await asyncio.to_thread(calculate_fitness_trends, rides, metric=metric, window=window)


@router.get("/monthly")
async def get_monthly_progression(current_user: dict = Depends(get_current_user)):
    """Get monthly aggregated metrics for athlete's rides."""
    from ...analytics.analytics_trends import calculate_monthly_progression

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = await RideRepository().list_all(athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id)
    return await asyncio.to_thread(calculate_monthly_progression, rides)


@router.get("/comparison")
async def get_period_comparison(
    period_days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    """Compare recent vs previous period for athlete's rides."""
    from ...analytics.analytics_trends import calculate_period_comparison

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [
        Ride(**r)
        for r in await RideRepository().list_all(
            athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id
        )
    ]
    return await asyncio.to_thread(calculate_period_comparison, rides, period_days=period_days)


@router.get("/zones")
async def get_zone_distributions(
    current_user: dict = Depends(get_current_user),
):
    """Aggregate power & heart-rate time-in-zone distributions.

    Builds the data behind the frontend "Training Zones" charts from
    the athlete's stored ride GPS samples. FTP and max HR are taken
    from the athlete profile when available, otherwise sensible defaults.
    """
    from ...analytics.zone_analysis import calculate_zone_distributions

    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete_id = _current_athlete_id(current_user)
    athlete = await AthleteRepository().get_by_id(athlete_id, tenant_id) or {}
    ftp = athlete.get("ftp_watts")
    max_hr = athlete.get("heart_rate_avg")
    rides = await RideRepository().list_all(athlete_id=athlete_id, tenant_id=tenant_id)
    return await asyncio.to_thread(calculate_zone_distributions, rides, ftp_watts=ftp, max_hr=max_hr)


@router.get("/projection")
async def get_volume_projection(
    target_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Project future training volume based on historical trend for athlete's rides."""
    from ...analytics.analytics_trends import calculate_training_volume_projection

    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = [
        Ride(**r)
        for r in await RideRepository().list_all(
            athlete_id=_current_athlete_id(current_user), tenant_id=tenant_id
        )
    ]
    return await asyncio.to_thread(calculate_training_volume_projection, rides, target_days=target_days)


@router.get("/multi-classify")
async def multi_classify_rides(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Classify athlete rides into multiple performance categories."""
    from ...analytics.multi_classifier import classify_rides

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    results = await asyncio.to_thread(classify_rides, rides)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "total_rides": len(results),
        "rides": [
            {
                "ride_id": r.ride_id,
                "date": r.date,
                "categories": r.categories,
                "primary_category": r.primary_category,
                "confidence": r.confidence,
                "metrics": r.metrics,
            }
            for r in results
        ],
    }


@router.get("/vip")
async def get_vip_prediction(
    athlete_id: int | None = None,
    ftp: float = Query(250.0),
    current_user: dict = Depends(get_current_user),
):
    """Get VIP (Very Important Performance) prediction for athlete."""
    from ...analytics.vip_predictor import estimate_vip

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    result = await asyncio.to_thread(estimate_vip, rides, athlete_ftp=ftp)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "probability_index": result.probability_index,
        "readiness_score": result.readiness_score,
        "recommendation": result.recommendation,
        "risk_factors": result.risk_factors,
    }


@router.get("/inactivity")
async def get_inactivity_report(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Estimate fitness decay after inactivity."""
    from ...analytics.inactivity_estimator import estimate_inactivity

    rides = _get_athlete_rides(athlete_id or current_user["id"], current_user)
    result = await asyncio.to_thread(estimate_inactivity, rides)
    return {
        "athlete_id": athlete_id or current_user["id"],
        "current_streak_days": result.current_streak_days,
        "estimated_ftp_loss_pct": result.estimated_ftp_loss_pct,
        "estimated_endurance_loss_pct": result.estimated_endurance_loss_pct,
        "recovery_plan_days": result.recovery_plan_days,
        "advice": result.advice,
    }


@router.get("/route-suggestions")
async def get_route_suggestions(
    athlete_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Suggest ride routes based on historical preferences."""
    from ...analytics.ride_route_estimator import estimate_route_preferences

    athlete_id = athlete_id or current_user["id"]
    athlete_data = await AthleteRepository().get_by_id(athlete_id)
    if not athlete_data:
        athlete_data = {"name": "Unknown", "preferred_terrain": "mixed", "ftp_watts": 250.0}
    athlete = AthleteProfile(**athlete_data)
    rides = _get_athlete_rides(athlete_id, current_user)
    suggestions = await asyncio.to_thread(estimate_route_preferences, athlete, rides)
    return {
        "athlete_id": athlete_id,
        "total_suggestions": len(suggestions),
        "routes": [
            {
                "name": s.name,
                "distance_km": s.distance_km,
                "elevation_gain_m": s.elevation_gain_m,
                "avg_speed_target_kmh": s.avg_speed_target_kmh,
                "duration_minutes": s.duration_minutes,
                "terrain": s.terrain,
                "rationale": s.rationale,
            }
            for s in suggestions
        ],
    }
