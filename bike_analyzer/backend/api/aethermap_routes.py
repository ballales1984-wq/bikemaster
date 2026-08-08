"""AetherMap spatial API routes.

Exposes CRUD and spatial query endpoints for geospatial objects
(POI, strade, percorsi, terreno) backed by AetherMapDB.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from aethermap.ai.models import Oggetto, Posizione
from aethermap.data.db import AetherMapDB

router = APIRouter()

_AETHERMAP_DB_PATH = os.getenv("AETHERMAP_DB_PATH")
_DB_CACHE: dict[str, AetherMapDB] = {}


def _get_db() -> AetherMapDB:
    path = os.getenv("AETHERMAP_DB_PATH") or ":memory:"
    if path not in _DB_CACHE:
        _DB_CACHE[path] = AetherMapDB(path)
    return _DB_CACHE[path]


class OggettoCreate(BaseModel):
    id: str
    tipo: str = Field(..., pattern="^(poi|strada|percorso|terreno|albero|montagna)$")
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    alt: float = Field(default=0.0)
    proprieta: dict[str, Any] = Field(default_factory=dict)
    geometria: dict[str, Any] | None = None


class OggettoUpdate(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    alt: float | None = Field(default=None)
    proprieta: dict[str, Any] | None = None
    geometria: dict[str, Any] | None = None


class OggettoOut(BaseModel):
    id: str
    tipo: str
    lat: float
    lon: float
    alt: float
    s2: str | None = None
    h3: str | None = None
    level: int = 0
    ecef_relative: tuple[float, float, float] | None = None
    proprieta: dict[str, Any] = {}
    geometria: dict[str, Any] = {}


def _to_out(obj: Oggetto) -> OggettoOut:
    return OggettoOut(
        id=obj.id,
        tipo=obj.tipo,
        lat=obj.posizione.lat,
        lon=obj.posizione.lon,
        alt=obj.posizione.alt,
        s2=obj.posizione.s2,
        h3=obj.posizione.h3,
        level=getattr(obj.posizione, "level", 0),
        ecef_relative=getattr(obj.posizione, "ecef_relative", None),
        proprieta=obj.proprieta,
        geometria=obj.geometria.model_dump() if obj.geometria else {},
    )


@router.get("/health")
async def aethermap_health():
    return {"status": "ok", "service": "aethermap"}


@router.post("/objects", response_model=OggettoOut)
async def create_object(payload: OggettoCreate, db: AetherMapDB = Depends(_get_db)):
    pos = Posizione.from_latlon(payload.lat, payload.lon, payload.alt)
    geom_data = payload.geometria or {}
    from aethermap.ai.models import Geometria
    geometria = Geometria(
        tipo=geom_data.get("tipo", "punto"),
        dati=geom_data.get("dati", {}),
        s2_cell_id=pos.s2,
        shape_type=geom_data.get("shape_type"),
        ecef_vertices=geom_data.get("ecef_vertices"),
        confidence=geom_data.get("confidence", 1.0),
    )
    obj = Oggetto(
        id=payload.id,
        tipo=payload.tipo,
        posizione=pos,
        geometria=geometria,
        proprieta=payload.proprieta,
    )
    try:
        db.add(obj)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_out(obj)


@router.get("/objects", response_model=list[OggettoOut])
async def list_objects(
    tipo: str | None = Query(default=None),
    db: AetherMapDB = Depends(_get_db),
):
    if tipo:
        objs = db.get_by_tipo(tipo)
    else:
        objs = list(db.iter_objects())
    return [_to_out(o) for o in objs]


@router.get("/objects/nearby", response_model=list[OggettoOut])
async def nearby_objects(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=5.0, ge=0.1, le=200),
    tipo: str | None = Query(default=None),
    db: AetherMapDB = Depends(_get_db),
):
    radius_m = radius_km * 1000.0
    results = db.query_radius(lat, lon, radius_m)
    if tipo:
        results = [o for o in results if o.tipo == tipo]
    return [_to_out(o) for o in results]


@router.get("/objects/bounds", response_model=list[OggettoOut])
async def objects_in_bounds(
    lat_min: float = Query(..., ge=-90, le=90),
    lat_max: float = Query(..., ge=-90, le=90),
    lon_min: float = Query(..., ge=-180, le=180),
    lon_max: float = Query(..., ge=-180, le=180),
    tipo: str | None = Query(default=None),
    db: AetherMapDB = Depends(_get_db),
):
    if lat_min > lat_max or lon_min > lon_max:
        raise HTTPException(status_code=400, detail="Invalid bounds: min must be <= max")
    results = db.query_bounds(lat_min, lat_max, lon_min, lon_max)
    if tipo:
        results = [o for o in results if o.tipo == tipo]
    return [_to_out(o) for o in results]


@router.get("/objects/within", response_model=list[OggettoOut])
async def objects_within(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    delta_km: float = Query(default=5.0, ge=0.1, le=200),
    tipo: str | None = Query(default=None),
    db: AetherMapDB = Depends(_get_db),
):
    dlat = delta_km / 111_320.0
    dlon = delta_km / (111_320.0 * max(abs(__import__("math").cos(__import__("math").radians(lat))), 0.1))
    results = db.query_bounds(lat - dlat, lat + dlat, lon - dlon, lon + dlon)
    if tipo:
        results = [o for o in results if o.tipo == tipo]
    return [_to_out(o) for o in results]


@router.get("/objects/{obj_id}", response_model=OggettoOut)
async def get_object(obj_id: str, db: AetherMapDB = Depends(_get_db)):
    obj = db.get(obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return _to_out(obj)


@router.put("/objects/{obj_id}", response_model=OggettoOut)
async def update_object(obj_id: str, payload: OggettoUpdate, db: AetherMapDB = Depends(_get_db)):
    obj = db.get(obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Object not found")
    if payload.lat is not None or payload.lon is not None or payload.alt is not None:
        lat = payload.lat if payload.lat is not None else obj.posizione.lat
        lon = payload.lon if payload.lon is not None else obj.posizione.lon
        alt = payload.alt if payload.alt is not None else obj.posizione.alt
        obj.posizione = Posizione.from_latlon(lat, lon, alt)
    if payload.proprieta is not None:
        obj.proprieta.update(payload.proprieta)
    if payload.geometria is not None:
        from aethermap.ai.models import Geometria
        obj.geometria = Geometria(
            tipo=payload.geometria.get("tipo", obj.geometria.tipo if obj.geometria else "punto"),
            dati=payload.geometria.get("dati", obj.geometria.dati if obj.geometria else {}),
            s2_cell_id=obj.posizione.s2,
            shape_type=payload.geometria.get("shape_type", getattr(obj.geometria, "shape_type", None)),
            ecef_vertices=payload.geometria.get("ecef_vertices", getattr(obj.geometria, "ecef_vertices", None)),
            confidence=payload.geometria.get("confidence", getattr(obj.geometria, "confidence", 1.0)),
        )
    try:
        db.add(obj)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_out(obj)


@router.delete("/objects/{obj_id}")
async def delete_object(obj_id: str, db: AetherMapDB = Depends(_get_db)):
    ok = db.remove(obj_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Object not found")
    return {"deleted": True}
