"""Import API routes for FIT, GPX, TCX, and batch uploads."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from bike_analyzer.backend.security import get_current_user
from bike_analyzer.backend.services.import_service import ImportService
from bike_analyzer.backend.settings import get_settings

router = APIRouter(prefix="/import", tags=["import"])
logger = logging.getLogger(__name__)
_s = get_settings()


@router.get("/providers")
async def list_import_providers():
    """Return the list of available import providers based on configuration."""
    return {
        "strava": bool(_s.strava_client_id and _s.strava_client_secret),
        "google_fit": bool(_s.google_fit_client_id and _s.google_fit_client_secret),
        "google_health": bool(_s.google_health_client_id and _s.google_health_client_secret),
        "wahoo": bool(_s.wahoo_client_id and _s.wahoo_client_secret),
        "garmin": bool(_s.garmin_consumer_key and _s.garmin_consumer_secret),
        "ble": True,
        "health_connect": True,
        "hr_24h": True,
    }


def _user_context(current_user: dict) -> tuple[int, int]:
    athlete_id = int(current_user.get("athlete_id") or current_user["id"])
    tenant_id = current_user.get("tenant_id", athlete_id)
    return athlete_id, tenant_id


@router.post("/fit")
async def import_fit(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    try:
        suffix = Path(file.filename or "upload.fit").suffix.lower()
        if suffix != ".fit":
            raise HTTPException(status_code=400, detail="Expected .fit file")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name
        result = ImportService.import_file(
            "fit",
            file_path=temp_path,
            name=file.filename,
            athlete_id=athlete_id,
            tenant_id=tenant_id,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("FIT import failed")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/gpx")
async def import_gpx(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
        result = ImportService.import_file(
            "gpx",
            content=content,
            name=file.filename,
            athlete_id=athlete_id,
            tenant_id=tenant_id,
        )
        return result
    except Exception as exc:
        logger.exception("GPX import failed")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/tcx")
async def import_tcx(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
        result = ImportService.import_file(
            "tcx",
            content=content,
            name=file.filename,
            athlete_id=athlete_id,
            tenant_id=tenant_id,
        )
        return result
    except Exception as exc:
        logger.exception("TCX import failed")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/multiple")
async def import_multiple(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    imported = []
    failed = []
    for file in files:
        try:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix == ".fit":
                with tempfile.NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
                    tmp.write(await file.read())
                    temp_path = tmp.name
                result = ImportService.import_file(
                    "fit",
                    file_path=temp_path,
                    name=file.filename,
                    athlete_id=athlete_id,
                    tenant_id=tenant_id,
                )
            elif suffix == ".gpx":
                text = (await file.read()).decode("utf-8", errors="replace")
                result = ImportService.import_file(
                    "gpx",
                    content=text,
                    name=file.filename,
                    athlete_id=athlete_id,
                    tenant_id=tenant_id,
                )
            elif suffix == ".tcx":
                text = (await file.read()).decode("utf-8", errors="replace")
                result = ImportService.import_file(
                    "tcx",
                    content=text,
                    name=file.filename,
                    athlete_id=athlete_id,
                    tenant_id=tenant_id,
                )
            else:
                failed.append({"name": file.filename, "error": "Unsupported format"})
                continue
            imported.append(result)
        except Exception as exc:
            failed.append({"name": file.filename, "error": str(exc)})
    return JSONResponse(content={"imported": imported, "failed": failed})


@router.get("/providers")
async def get_import_providers(current_user: dict = Depends(get_current_user)):
    return {
        "google_fit": True,
        "google_health": False,
        "wahoo": False,
        "strava": False,
        "garmin": False,
        "health_connect": False,
    }
