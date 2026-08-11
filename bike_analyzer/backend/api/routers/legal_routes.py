"""Legal API routes."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from ...security import get_current_user
from ..routes import _ensure_athlete_access
from ..schemas import MeasurementCreate
from ...analytics.repositories.legal_repository import LegalRepository

router = APIRouter(prefix="/legal", tags=["legal"])


@router.post("/consent")
async def record_consent(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Record user consent."""
    consent_type = str(payload.get("consent_type", "")).strip()
    granted = bool(payload.get("granted", True))
    source = str(payload.get("source", "web"))
    if not consent_type:
        raise HTTPException(status_code=400, detail="consent_type is required")
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    LegalRepository.save_consent(
        athlete_id=athlete_id,
        consent_type=consent_type,
        granted=granted,
        source=source,
        tenant_id=current_user.get("tenant_id", current_user["id"]),
    )
    return {"status": "recorded", "consent_type": consent_type, "granted": granted}


@router.get("/consent")
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    """Get user consents."""
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    return {"consents": LegalRepository.get_consents_by_athlete(athlete_id)}


@router.post("/accept")
async def record_legal_acceptance(
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """Record legal acceptance."""
    acceptance_type = str(payload.get("acceptance_type", "")).strip()
    version = str(payload.get("version", "")).strip()
    source = str(payload.get("source", "web"))
    if not acceptance_type or not version:
        raise HTTPException(status_code=400, detail="acceptance_type and version are required")
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    LegalRepository.save_legal_acceptance(
        athlete_id=athlete_id,
        acceptance_type=acceptance_type,
        version=version,
        source=source,
        tenant_id=current_user.get("tenant_id", current_user["id"]),
    )
    return {"status": "recorded", "acceptance_type": acceptance_type, "version": version}


@router.get("/acceptances")
async def get_my_acceptances(current_user: dict = Depends(get_current_user)):
    """Get legal acceptances."""
    athlete_id = current_user.get("athlete_id") or current_user["id"]
    return {"acceptances": LegalRepository.get_legal_acceptances_by_athlete(athlete_id)}


@router.get("/export-all")
async def export_all_my_data(current_user: dict = Depends(get_current_user)):
    """Export all user data as JSON."""
    import json

    from fastapi.responses import FileResponse

    from ...analytics.services.export_service import ExportService

    athlete_id = current_user.get("athlete_id") or current_user["id"]
    tenant_id = current_user.get("tenant_id", current_user["id"])
    now = datetime.now(UTC).isoformat()
    path = f"bikemaster_export_{current_user['id']}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    export_data = ExportService.export_all_my_data(current_user["id"], tenant_id)
    export_data["exported_at"] = now
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    return FileResponse(path, media_type="application/json", filename=path, background=BackgroundTask(os.remove, path))


@router.delete("/delete-account")
async def delete_my_account(current_user: dict = Depends(get_current_user)):
    """Delete user account."""
    from ...analytics.repositories.athlete_repository import AthleteRepository

    athlete_id = current_user.get("athlete_id") or current_user["id"]
    tenant_id = current_user.get("tenant_id", current_user["id"])
    athlete = AthleteRepository().get_by_id(athlete_id, tenant_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    AthleteRepository().delete(athlete_id, current_user["id"])
    return {"status": "deleted"}
