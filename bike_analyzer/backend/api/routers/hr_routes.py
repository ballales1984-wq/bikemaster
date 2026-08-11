"""HR monitoring API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..routes import _current_athlete_id, get_current_user
from ..schemas import Hr24hSummary, HrMonitoringSettings, HrSamplesBulk, SensorSamplesBulk

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/settings")
async def get_hr_settings_route(current_user: dict = Depends(get_current_user)):
    """Return HR 24h monitoring settings for the current athlete."""
    from ...db.database import get_hr_settings

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    settings = get_hr_settings(athlete_id, tenant_id)
    if settings is None:
        settings = {
            "enabled": True,
            "interval_seconds": 30,
            "source": "ble",
            "device_id": None,
            "max_hr": None,
            "resting_hr": None,
        }
    settings.pop("id", None)
    settings.pop("athlete_id", None)
    settings.pop("tenant_id", None)
    if "enabled" in settings:
        settings["enabled"] = bool(settings["enabled"])
    return settings


@router.put("/settings")
async def upsert_hr_settings_route(
    settings_data: HrMonitoringSettings,
    current_user: dict = Depends(get_current_user),
):
    """Create or update HR 24h monitoring settings."""
    from ...db.database import upsert_hr_settings

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    settings = upsert_hr_settings(
        athlete_id,
        settings_data.model_dump(),
        tenant_id=tenant_id,
    )
    settings.pop("id", None)
    settings.pop("athlete_id", None)
    settings.pop("tenant_id", None)
    if "enabled" in settings:
        settings["enabled"] = bool(settings["enabled"])
    return settings


@router.post("/samples")
async def log_hr_samples_route(
    samples: HrSamplesBulk,
    current_user: dict = Depends(get_current_user),
):
    """Persist heart-rate samples from BLE or other sources (bulk)."""
    from ...db.database import log_hr_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = log_hr_samples(
        athlete_id,
        [s.model_dump() for s in samples.samples],
        source=samples.source or "ble",
        tenant_id=tenant_id,
    )
    return {"saved": count}


@router.get("/24h")
async def get_hr_24h_route(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
):
    """Return raw heart-rate samples for the last *hours* hours (oldest-first)."""
    from ...db.database import get_hr_24h_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    samples = get_hr_24h_samples(athlete_id, hours=hours, tenant_id=tenant_id)
    return {"samples": samples}


@router.get("/summary", response_model=Hr24hSummary | None)
async def get_hr_daily_summary_route(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Return per-day HR summary for the last *days* days (latest day)."""
    from ...db.database import get_hr_daily_summary

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    history = get_hr_daily_summary(athlete_id, days=days, tenant_id=tenant_id)
    if not history:
        return None
    return Hr24hSummary(**history[-1])


@router.get("/summary/history")
async def get_hr_summary_history_route(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Return the full per-day HR history for charting trends."""
    from ...db.database import get_hr_daily_summary

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    history = get_hr_daily_summary(athlete_id, days=days, tenant_id=tenant_id)
    return {"history": history}


@router.delete("/samples")
async def delete_hr_samples_route(
    older_than: str | None = Query(default=None, description="ISO timestamp; delete samples older than this"),
    current_user: dict = Depends(get_current_user),
):
    """Delete HR samples, optionally older than a given timestamp (cleanup)."""
    from ...db.database import delete_hr_samples

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = delete_hr_samples(athlete_id, tenant_id=tenant_id, older_than=older_than)
    return {"deleted": count}


@router.post("/sensor")
async def log_sensor_data_route(
    payload: SensorSamplesBulk,
    current_user: dict = Depends(get_current_user),
):
    """Persist raw BLE sensor readings (heart-rate, GPS, accelerometer)."""
    from ...db.database import log_sensor_data

    athlete_id = _current_athlete_id(current_user)
    tenant_id = current_user.get("tenant_id", athlete_id)
    count = log_sensor_data(
        athlete_id,
        [s.model_dump() for s in payload.samples],
        tenant_id=tenant_id,
    )
    return {"saved": count}
