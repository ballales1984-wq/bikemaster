"""BikeMaster 2.0 analysis API (knowledge/model-driven engine).

Espone l'AI Orchestrator del motore BikeMaster 2.0 su ``/api/v1/bm2``.
Ogni risposta riporta sempre, per ogni algoritmo: risultato + formula usata
+ dati utilizzati + precisione + fonte (vedi ``bike_analyzer.bm2``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bike_analyzer.bm2.adapters import ride_to_analysis_context
from bike_analyzer.bm2.algorithms import ALL_ALGORITHMS
from bike_analyzer.bm2.orchestrator import AIOrchestrator
from bike_analyzer.bm2.simulation import ScenarioOverride, SimulationEngine
from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride
from bike_analyzer.core.physics import RiderBikeParams, validate_ride_power

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


def _to_gps(p: dict) -> GPSPoint:
    point = dict(p)
    ts = point.get("timestamp")
    if isinstance(ts, str):
        point["timestamp"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return GPSPoint(**point)


def _ride_from_request(req: Bm2SimulateRideRequest, current_user: dict) -> Ride:
    """Carica la ``Ride`` dal flusso prodotto (DB + access control) o da payload inline."""
    if req.ride_id is not None:
        from ..db.database import get_ride as _get_ride
        from .routes import _ensure_ride_access

        ride_dict = _get_ride(req.ride_id)
        if not ride_dict:
            raise HTTPException(status_code=404, detail="Ride not found")
        _ensure_ride_access(ride_dict, current_user)
        gps = [_to_gps(p) for p in (ride_dict.get("gps_points") or [])]
        ride = Ride(**{k: v for k, v in ride_dict.items() if k in Ride.__dataclass_fields__})
        ride.gps_points = gps
        return ride

    if not req.gps_points:
        raise HTTPException(status_code=400, detail="Serve ride_id o gps_points inline")
    gps = [_to_gps(p) for p in req.gps_points]
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
        athlete = (
            AthleteProfile(**{k: v for k, v in req.athlete.items()
                              if k in AthleteProfile.__dataclass_fields__})
            if req.athlete else None
        )
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


class Bm2ValidateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    ride_id: int | None = None
    athlete: dict[str, Any] = Field(default_factory=dict)
    bike: dict[str, Any] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    override: dict[str, Any] = Field(default_factory=dict)
    gps_points: list[dict[str, Any]] = Field(default_factory=list)


def _rider_bike_params(bike: dict[str, Any]) -> RiderBikeParams:
    return RiderBikeParams(
        rider_mass_kg=float(bike.get("weight", 70.0)),
        bike_mass_kg=float(bike.get("bike_weight", 8.0)),
        cda=float(bike.get("cda", 0.40)),
        crr=float(bike.get("crr", 0.005)),
        drivetrain_efficiency=float(bike.get("drivetrain_efficiency", 0.25)),
    )


@bm2_router.post("/validate")
async def validate(
    req: Bm2ValidateRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """Valida il kernel fisico contro i power-meter di una Ride reale.

    Ritorna le metriche di errore (MAE/RMSE/bias/R²) tra potenza stimata e
    potenza misurata. 422 se la ride non ha abbastanza dati power-meter.
    """
    try:
        ride = _ride_from_request(req, current_user)
        params = _rider_bike_params(req.bike)
        wind = req.world.get("wind_speed")
        result = validate_ride_power(ride, params, wind_ms=wind if wind is not None else 0.0)
        if result is None:
            raise HTTPException(
                status_code=422,
                detail="Dati power-meter insufficienti per la validazione",
            )
        return {"ride_id": req.ride_id, "validation": result.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
