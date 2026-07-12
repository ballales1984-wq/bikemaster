"""BikeMaster 2.0 analysis API (knowledge/model-driven engine).

Espone l'AI Orchestrator del motore BikeMaster 2.0 su ``/api/v1/bm2``.
Ogni risposta riporta sempre, per ogni algoritmo: risultato + formula usata
+ dati utilizzati + precisione + fonte (vedi ``bike_analyzer.bm2``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bike_analyzer.bm2.adapters import ride_to_analysis_context
from bike_analyzer.bm2.algorithms import ALL_ALGORITHMS
from bike_analyzer.bm2.orchestrator import AIOrchestrator
from bike_analyzer.bm2.simulation import ScenarioOverride, SimulationEngine
from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride
from ..security import get_current_user

bm2_router = APIRouter()


class Bm2AskRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    question: str
    athlete: dict[str, Any] = Field(default_factory=dict)
    bike: dict[str, Any] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    gps_points: list[dict[str, Any]] = Field(default_factory=list)
    sensors: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] | None = None


def _build_raw(req: Bm2AskRequest) -> dict:
    return {
        "athlete": req.athlete,
        "bike": req.bike,
        "world": req.world,
        "gps_points": req.gps_points,
        "sensors": req.sensors,
    }


@bm2_router.get("/models")
async def list_models() -> dict:
    """Elenco degli algoritmi disponabili nel Model Engine."""
    return {
        "models": [
            {"name": a.__name__, "formula": a.formula, "unit": a.unit,
             "description": a.description}
            for a in ALL_ALGORITHMS
        ]
    }


@bm2_router.post("/ask")
async def ask(req: Bm2AskRequest) -> dict:
    """Risponde a una domanda usando gli agenti e gli algoritmi opportuni."""
    try:
        return AIOrchestrator().answer(req.question, _build_raw(req), req.extra)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@bm2_router.post("/simulate")
async def simulate(req: Bm2AskRequest) -> dict:
    """Esegue uno scenario \"what if\" (es. \"Se peso -5 kg\")."""
    try:
        return AIOrchestrator().answer(req.question, _build_raw(req), req.extra)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class Bm2SimulateRideRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    ride_id: int | None = None
    override: dict[str, Any] = Field(default_factory=dict)
    athlete: dict[str, Any] = Field(default_factory=dict)
    bike: dict[str, Any] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    gps_points: list[dict[str, Any]] = Field(default_factory=list)


def _ride_from_request(req: Bm2SimulateRideRequest, current_user: dict) -> Ride:
    """Carica la ``Ride`` dal flusso prodotto (DB + access control) o da payload inline."""
    if req.ride_id is not None:
        from ..db.database import get_ride as _get_ride
        from .routes import _ensure_ride_access

        ride_dict = _get_ride(req.ride_id)
        if not ride_dict:
            raise HTTPException(status_code=404, detail="Ride not found")
        _ensure_ride_access(ride_dict, current_user)
        gps = [GPSPoint(**p) for p in (ride_dict.get("gps_points") or [])]
        ride = Ride(**{k: v for k, v in ride_dict.items() if k in Ride.__dataclass_fields__})
        ride.gps_points = gps
        return ride

    if not req.gps_points:
        raise HTTPException(status_code=400, detail="Serve ride_id o gps_points inline")
    gps = [GPSPoint(**p) for p in req.gps_points]
    ride = Ride(gps_points=gps, weight_kg=float(req.bike.get("weight", 70.0)))
    return ride


def _context_kwargs(req: Bm2SimulateRideRequest) -> dict:
    kwargs: dict[str, Any] = {}
    for src, key, field in (
        (req.bike, "weight", "bike_weight_kg"),
        (req.bike, "cda", "cda"),
        (req.bike, "crr", "crr"),
        (req.bike, "drivetrain_efficiency", "drivetrain_efficiency"),
        (req.world, "wind_speed", "wind_speed_ms"),
        (req.world, "temperature", "temperature_c"),
        (req.world, "surface", "surface"),
    ):
        if src.get(key) is not None:
            kwargs[field] = src[key]
    return kwargs


@bm2_router.post("/simulate-ride")
async def simulate_ride(
    req: Bm2SimulateRideRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """What-if su una Ride reale del prodotto (by id o payload inline)."""
    try:
        ride = _ride_from_request(req, current_user)
        athlete = AthleteProfile(**{k: v for k, v in req.athlete.items()
                                    if k in AthleteProfile.__dataclass_fields__}) or None
        if not req.athlete:
            athlete = None
        override_fields = {k: v for k, v in req.override.items()
                           if k in ScenarioOverride.__dataclass_fields__}
        override = ScenarioOverride(**override_fields)
        ctx = ride_to_analysis_context(ride, athlete, **_context_kwargs(req))
        comp = SimulationEngine(ALL_ALGORITHMS).compare(ctx, override)
        return {
            "ride_id": req.ride_id,
            "comparison": comp.to_dict(),
            "summary": comp.summary(),
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
