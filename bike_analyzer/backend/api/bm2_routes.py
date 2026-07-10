"""BikeMaster 2.0 analysis API (knowledge/model-driven engine).

Espone l'AI Orchestrator del motore BikeMaster 2.0 su ``/api/v1/bm2``.
Ogni risposta riporta sempre, per ogni algoritmo: risultato + formula usata
+ dati utilizzati + precisione + fonte (vedi ``bike_analyzer.bm2``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bike_analyzer.bm2.algorithms import ALL_ALGORITHMS
from bike_analyzer.bm2.orchestrator import AIOrchestrator

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
