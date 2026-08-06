from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from aethermap.core.coordinates import geodetic_to_cube, h3_cell, s2_cell_id


def _now() -> datetime:
    return datetime.now(UTC)


class Confidenza(BaseModel):
    valore: float = Field(ge=0.0, le=1.0, default=1.0)
    incertezza_spaziale_m: float = 0.0
    incertezza_temporale_s: float = 0.0


class Posizione(BaseModel):
    lat: float
    lon: float
    alt: float = 0.0
    cube_face: int | None = None
    cube_u: float | None = None
    cube_v: float | None = None
    s2: str | None = None
    h3: str | None = None

    @classmethod
    def from_latlon(cls, lat: float, lon: float, alt: float = 0.0) -> Posizione:
        c = geodetic_to_cube(lat, lon)
        try:
            s2 = s2_cell_id(lat, lon)
        except RuntimeError:
            s2 = None
        try:
            h3 = h3_cell(lat, lon)
        except RuntimeError:
            h3 = None
        return cls(
            lat=lat,
            lon=lon,
            alt=alt,
            cube_face=c.face,
            cube_u=round(c.u, 6),
            cube_v=round(c.v, 6),
            s2=s2,
            h3=h3,
        )


class Geometria(BaseModel):
    tipo: str = "punto"
    dati: dict[str, Any] = {}


class Stato(BaseModel):
    campi: dict[str, Any] = {}
    t: datetime = Field(default_factory=_now)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class Sorgente(BaseModel):
    tipo: str
    id: str
    ts: datetime = Field(default_factory=_now)


class Relazione(BaseModel):
    tipo: str
    target_id: str
    peso: float = 1.0


class Oggetto(BaseModel):
    id: str
    tipo: str
    posizione: Posizione
    geometria: Geometria = Geometria()
    proprieta: dict[str, Any] = {}
    affidabilita: Confidenza = Confidenza()
    sorgenti: list[Sorgente] = []
    cronologia: list[Stato] = []
    relazioni: list[Relazione] = []
    stale_after_s: float | None = None


class Proposta(BaseModel):
    target_id: str | None = None
    nuovo: bool = False
    posizione: Posizione | None = None
    tipo: str | None = None
    campo: str
    valore: Any
    confidence: float = Field(ge=0.0, le=1.0)
    motivazione: str = ""
    ts: datetime = Field(default_factory=_now)
