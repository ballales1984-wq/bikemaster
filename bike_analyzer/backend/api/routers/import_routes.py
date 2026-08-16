"""Import API routes for FIT, GPX, TCX, and batch uploads."""

from __future__ import annotations

import json
import logging
import secrets
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from bike_analyzer.backend.ingestion.google_health import (
    exchange_code_for_token,
    get_authorization_url,
    google_health_to_rides,
)
from bike_analyzer.backend.ingestion.google_oauth_store import (
    delete_google_token,
    ensure_google_tokens_table,
    store_google_token,
)
from bike_analyzer.backend.redis_client import cache_delete, cache_set, cached
from bike_analyzer.backend.security import get_current_user, get_optional_current_user
from bike_analyzer.backend.services.import_service import ImportService
from bike_analyzer.backend.settings import get_settings

router = APIRouter(prefix="/import", tags=["import"])
logger = logging.getLogger(__name__)
_s = get_settings()
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _build_redirect_uri(request: Request, path: str) -> str:
    client_host = request.client.host if request.client else ""
    if client_host in ("127.0.0.1", "localhost", "0.0.0.0"):
        proto = request.url.scheme
        host = request.headers.get("host") or request.url.netloc
        return f"{proto}://{host}{path}"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    host_lower = host.lower()
    if host_lower.endswith(".ngrok-free.dev") or host_lower.endswith(".vercel.app") or host_lower.endswith(".onrender.com"):
        proto = "https"
    return f"{proto}://{host}{path}"


async def _validate_file_size(file: UploadFile) -> None:
    size = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
    await file.seek(0)


@router.get("/providers")
async def get_import_providers(current_user: dict | None = Depends(get_optional_current_user)):
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
        await _validate_file_size(file)
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
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/gpx")
async def import_gpx(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    try:
        await _validate_file_size(file)
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
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/tcx")
async def import_tcx(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    athlete_id, tenant_id = _user_context(current_user)
    try:
        await _validate_file_size(file)
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
        raise HTTPException(status_code=400, detail=str(exc)) from None


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
            await _validate_file_size(file)
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


@router.get("/strava/auth")
async def strava_auth():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/strava/callback")
async def strava_callback():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/google-fit/auth")
async def google_fit_auth():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/google-fit/callback")
async def google_fit_callback():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/garmin/auth")
async def garmin_auth():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/garmin/callback")
async def garmin_callback():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/wahoo/auth")
async def wahoo_auth():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/wahoo/callback")
async def wahoo_callback():
    return JSONResponse(content={"detail": "Not implemented"})


@router.delete("/strava/disconnect")
async def strava_disconnect():
    return JSONResponse(content={"detail": "Not implemented"})


@router.delete("/google-fit/disconnect")
async def google_fit_disconnect():
    return JSONResponse(content={"detail": "Not implemented"})


@router.delete("/garmin/disconnect")
async def garmin_disconnect():
    return JSONResponse(content={"detail": "Not implemented"})


@router.delete("/wahoo/disconnect")
async def wahoo_disconnect():
    return JSONResponse(content={"detail": "Not implemented"})


@router.get("/google-health/auth")
async def google_health_auth(request: Request):
    if not _s.google_health_client_id or not _s.google_health_client_secret:
        raise HTTPException(status_code=500, detail="Google Health non configurato")
    redirect_uri = request.query_params.get("redirect_uri") or _build_redirect_uri(request, "/api/v1/import/google-health")
    state = secrets.token_urlsafe(32)
    await cache_set(f"oauth:state:{state}", {"redirect_uri": redirect_uri}, ttl=600)
    auth_url = get_authorization_url(
        client_id=_s.google_health_client_id,
        redirect_uri=redirect_uri,
        state=state,
    )
    return {"auth_url": auth_url, "state": state}


@router.get("/google-health")
async def google_health_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return HTMLResponse(
            content="<html><body><script>window.opener.postMessage({type:'google-health-error',error:'missing_code_or_state',error_description:'Codice o stato mancante'},'*');window.close();</script></body></html>",
            media_type="text/html",
        )
    cached_state = await cached(f"oauth:state:{state}")
    if not cached_state:
        return HTMLResponse(
            content="<html><body><script>window.opener.postMessage({type:'google-health-error',error:'invalid_state',error_description:'Stato non valido o scaduto'},'*');window.close();</script></body></html>",
            media_type="text/html",
        )
    await cache_delete(f"oauth:state:{state}")
    return HTMLResponse(
        content=f"<html><body><script>window.opener.postMessage({{type:'google-health-success',code:{json.dumps(code)}}},'*');window.close();</script></body></html>",
        media_type="text/html",
    )


@router.post("/google-health")
async def google_health_connect(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Codice mancante")
    redirect_uri = _build_redirect_uri(request, "/api/v1/import/google-health")
    token_data = exchange_code_for_token(
        client_id=_s.google_health_client_id,
        client_secret=_s.google_health_client_secret,
        code=code,
        redirect_uri=redirect_uri,
    )
    athlete_id = int(current_user.get("athlete_id") or current_user["id"])
    ensure_google_tokens_table()
    store_google_token(athlete_id=athlete_id, provider="google_health", token_data=token_data)
    from bike_analyzer.backend.db.repositories.ride_repository import save_ride
    rides = google_health_to_rides(
        access_token=token_data["access_token"],
        athlete_id=athlete_id,
        days=180,
    )
    imported = 0
    for ride in rides:
        try:
            save_ride(ride)
            imported += 1
        except Exception:
            pass
    return {"count": imported}


@router.delete("/google-health/disconnect")
async def google_health_disconnect(
    current_user: dict = Depends(get_current_user),
):
    athlete_id = int(current_user.get("athlete_id") or current_user["id"])
    delete_google_token(athlete_id, "google_health")
    return {"detail": "Disconnesso"}
