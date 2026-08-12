"""Performance analytics REST API (FTP, power metrics, NP/IF/TSS)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from bike_analyzer.backend.analytics.performance_service import (
    get_ftp_history as _get_ftp_history,
)
from bike_analyzer.backend.analytics.performance_service import (
    get_latest_ftp,
    recompute_athlete_performance,
    record_ftp,
    save_ride_performance,
)
from bike_analyzer.backend.analytics.performance_service import (
    get_performance_metrics as _get_performance_metrics,
)
from bike_analyzer.backend.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


class FtpRecordRequest(BaseModel):
    ftp_watts: float
    date: str | None = None
    source: str = "test"
    note: str | None = None


class FtpEstimateRequest(BaseModel):
    test_power: float
    test_duration_min: float
    ftp_fraction: float = 0.95


class ComputeRequest(BaseModel):
    power_stream: list[float]
    duration_seconds: float | None = None
    ftp: float | None = None


def _current_athlete_id(current_user: dict) -> int:
    try:
        return int(current_user.get("athlete_id") or current_user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user token") from exc


@router.get("/metrics")
async def get_performance_metrics(
    athlete_id: int = Query(...),
    ride_id: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Return persisted power metrics for an athlete."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    metrics = _get_performance_metrics(athlete_id, tenant_id=tenant_id, ride_id=ride_id)
    return {"metrics": metrics}


@router.get("/ftp")
async def get_ftp_history(
    athlete_id: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Return FTP history for an athlete."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    history = _get_ftp_history(athlete_id, tenant_id=tenant_id)
    latest = get_latest_ftp(athlete_id, tenant_id=tenant_id)
    return {"history": history, "latest_ftp": latest}


@router.post("/ftp")
async def record_ftp_endpoint(
    payload: FtpRecordRequest,
    athlete_id: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Record or update FTP for an athlete on a specific date."""
    tenant_id = current_user.get("tenant_id", current_user["id"])
    result = record_ftp(
        athlete_id=athlete_id,
        ftp_watts=payload.ftp_watts,
        date=payload.date,
        source=payload.source,
        note=payload.note,
        tenant_id=tenant_id,
    )
    return result


@router.post("/ftp/estimate")
async def estimate_ftp_endpoint(payload: FtpEstimateRequest):
    """Estimate FTP from a threshold test."""
    from bike_analyzer.backend.analytics.performance import estimate_ftp_from_test

    estimated = estimate_ftp_from_test(payload.test_power, payload.test_duration_min, payload.ftp_fraction)
    return {"estimated_ftp": estimated}


@router.post("/ride/{ride_id}/compute")
async def compute_ride_metrics(
    ride_id: int,
    athlete_id: int = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """Compute and persist power metrics for a ride."""
    from bike_analyzer.backend.db.database import get_ride

    tenant_id = current_user.get("tenant_id", current_user["id"])
    ride = get_ride(ride_id, tenant_id=tenant_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if not current_user.get("is_admin") and int(ride.get("athlete_id", 0)) != int(athlete_id):
        raise HTTPException(status_code=403, detail="Access denied to this ride")
    ftp = get_latest_ftp(athlete_id, tenant_id=tenant_id)
    result = save_ride_performance(athlete_id, ride, ftp, tenant_id=tenant_id)
    if result is None:
        raise HTTPException(status_code=422, detail="No power data in ride")
    return {"ride_id": ride_id, "metrics": result}


@router.post("/compute")
async def compute_from_stream(payload: ComputeRequest):
    """Compute power metrics from a raw power stream without persisting."""
    from bike_analyzer.backend.analytics.performance import (
        calculate_intensity_factor,
        calculate_normalized_power,
        calculate_tss,
    )

    np_value = calculate_normalized_power(payload.power_stream)
    if np_value is None:
        return {
            "average_power": sum(payload.power_stream) / len(payload.power_stream),
            "normalized_power": None,
            "intensity_factor": None,
            "tss": None,
        }
    ftp = payload.ftp
    if ftp is not None and ftp > 0:
        if_value = calculate_intensity_factor(np_value, ftp)
        duration = payload.duration_seconds or len(payload.power_stream)
        tss_value = calculate_tss(np_value, ftp, duration, if_value)
    else:
        if_value = None
        tss_value = None
    return {
        "average_power": sum(payload.power_stream) / len(payload.power_stream),
        "normalized_power": np_value,
        "intensity_factor": if_value,
        "tss": tss_value,
    }


@router.post("/recompute")
async def recompute_all(current_user: dict = Depends(get_current_user)):
    """Recompute performance metrics for all rides of the current athlete."""
    from bike_analyzer.backend.db.database import get_rides_by_athlete

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", current_user["id"])
    rides = get_rides_by_athlete(athlete_id, tenant_id=tenant_id)
    saved = recompute_athlete_performance(athlete_id, rides, tenant_id=tenant_id)
    return {"processed": len(saved), "metrics": saved}
