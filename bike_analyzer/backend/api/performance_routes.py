"""Performance analytics API (NP/FTP/TSS) su ``/api/v1/performance``.

Espone il calcolo e la lettura delle metriche di potenza per ride e dello
storico FTP dell'atleta corrente, basandosi su ``analytics.performance_service``.
Tutti gli endpoint richiedono autenticazione (Bearer JWT) e applicano il
controllo di accesso per atleta (owner o admin).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..db.database import get_ride, get_rides_by_athlete
from ..models.models import Ride
from ..security import get_current_user
from ..api.routes import _ensure_athlete_access, _user_id
from ..analytics import performance_service as svc
from ..analytics.performance import (
    calculate_normalized_power,
    calculate_intensity_factor,
    calculate_tss,
    estimate_ftp_from_test,
)

performance_router = APIRouter(prefix="/performance", tags=["performance"])


class FtpRecordRequest(BaseModel):
    """Registra un valore FTP (test di soglia o stima)."""

    model_config = ConfigDict(extra="forbid")

    ftp_watts: float = Field(..., gt=0, description="Valore FTP in watt")
    date: str | None = Field(None, description="Data YYYY-MM-DD (default: oggi)")
    source: str = Field("test", description="Provenienza: test, ride, estimate")
    note: str | None = None


class FtpTestRequest(BaseModel):
    """Stima FTP da un test di soglia (media potenza su durata nota)."""

    model_config = ConfigDict(extra="forbid")

    test_power: float = Field(..., gt=0, description="Media potenza del test (W)")
    test_duration_min: float = Field(20.0, gt=0, description="Durata test in minuti")
    ftp_fraction: float = Field(0.95, gt=0, description="Frazione (20min=0.95, 60min=1.0)")


class RidePowerRequest(BaseModel):
    """Stream di potenza 1Hz per il calcolo on-the-fly di una ride."""

    model_config = ConfigDict(extra="forbid")

    power_stream: list[float] = Field(..., min_length=1, description="Stream potenza (W) a 1Hz")
    duration_seconds: float | None = Field(None, gt=0, description="Durata uscita in secondi")
    ftp: float | None = Field(None, gt=0, description="FTP noto per IF/TSS (opzionale)")


def _current_athlete_id(current_user: dict) -> int:
    """Risolve l'athlete_id dal token utente corrente."""
    return _user_id(current_user)


@performance_router.get("/metrics")
async def list_performance_metrics(
    ride_id: int | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Restituisce le metriche di potenza persistite dell'atleta corrente."""
    athlete_id = _current_athlete_id(current_user)
    _ensure_athlete_access(athlete_id, current_user)
    rows = svc.get_performance_metrics(athlete_id, ride_id=ride_id)
    return {"athlete_id": athlete_id, "metrics": rows}


@performance_router.get("/ftp")
async def list_ftp_history(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Restituisce lo storico FTP dell'atleta corrente (ordinato per data)."""
    athlete_id = _current_athlete_id(current_user)
    _ensure_athlete_access(athlete_id, current_user)
    history = svc.get_ftp_history(athlete_id)
    latest = history[-1]["ftp_watts"] if history else None
    return {"athlete_id": athlete_id, "latest_ftp": latest, "history": history}


@performance_router.post("/ftp")
async def create_ftp_record(
    payload: FtpRecordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Registra (UPSERT per data) un valore FTP per l'atleta corrente."""
    athlete_id = _current_athlete_id(current_user)
    _ensure_athlete_access(athlete_id, current_user)
    if not (1 <= payload.ftp_watts <= 2000):
        raise HTTPException(status_code=422, detail="ftp_watts fuori range plausibile (1-2000)")
    record = svc.record_ftp(
        athlete_id,
        ftp_watts=payload.ftp_watts,
        date=payload.date,
        source=payload.source,
        note=payload.note,
    )
    return record


@performance_router.post("/ftp/estimate")
async def estimate_ftp(
    payload: FtpTestRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Stima FTP da un test di soglia (media power * frazione)."""
    ftp = estimate_ftp_from_test(
        payload.test_power, payload.test_duration_min, payload.ftp_fraction
    )
    if ftp is None:
        raise HTTPException(status_code=400, detail="Impossibile stimare FTP dai dati forniti")
    return {"estimated_ftp": ftp}


@performance_router.post("/ride/{ride_id}/compute")
async def compute_ride_metrics(
    ride_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Ricalcola e persiste le metriche di potenza di una ride esistente.

    Usa lo stream di potenza dai gps_points della ride. Se l'atleta ha un FTP
    noto, lo usa per IF/TSS; altrimenti prova a stimarlo dalla ride.
    """
    athlete_id = _current_athlete_id(current_user)
    ride = get_ride(ride_id)
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride non trovata")
    _ensure_athlete_access(athlete_id, current_user)
    if ride.get("athlete_id") != athlete_id and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied to this ride")

    ftp = svc.get_latest_ftp(athlete_id)
    result = svc.save_ride_performance(athlete_id, ride, ftp)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail="Nessuno stream di potenza disponibile per questa ride",
        )
    return {"ride_id": ride_id, "metrics": result}


@performance_router.post("/compute")
async def compute_power_from_stream(
    payload: RidePowerRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Calcola NP/IF/TSS on-the-fly da uno stream di potenza (senza persistere)."""
    athlete_id = _current_athlete_id(current_user)
    _ensure_athlete_access(athlete_id, current_user)
    np_value = calculate_normalized_power(payload.power_stream)
    if np_value is None:
        raise HTTPException(status_code=422, detail="Stream di potenza insufficiente o non valido")
    if_count = calculate_intensity_factor(np_value, payload.ftp)
    tss = calculate_tss(np_value, payload.ftp, payload.duration_seconds, if_count)
    avg = round(sum(p for p in payload.power_stream if p is not None) / len(payload.power_stream), 1)
    return {
        "average_power": avg,
        "normalized_power": np_value,
        "intensity_factor": if_count,
        "tss": tss,
    }


@performance_router.post("/recompute")
async def recompute_all(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Ricalcola e persiste le metriche per tutte le ride dell'atleta corrente."""
    athlete_id = _current_athlete_id(current_user)
    _ensure_athlete_access(athlete_id, current_user)
    rides = get_rides_by_athlete(athlete_id)
    saved = svc.recompute_athlete_performance(
        athlete_id, [dict(r) if not isinstance(r, dict) else r for r in rides]
    )
    return {"athlete_id": athlete_id, "processed": len(saved), "metrics": saved}


__all__ = ["performance_router"]
