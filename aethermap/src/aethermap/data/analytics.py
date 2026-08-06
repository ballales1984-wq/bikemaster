"""AetherMap Fase 2 — analytics spaziali e temporali.

Implementa aggregazioni richieste da Fase 2 §10:
- densità per cella S2
- conteggio per categoria in raggio geodetico
- aggregazione temporale su campi dinamici della cronologia
- helper H3 (richiede `h3` installato)
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from aethermap.ai.models import Oggetto


def _utcnow() -> datetime:
    return datetime.now(UTC)


def spatial_density_by_s2(objects: Iterable[Oggetto]) -> dict[str, int]:
    counts: dict[str, int] = Counter()
    for obj in objects:
        s2 = getattr(obj.posizione, "s2", None) or ""
        if s2:
            counts[s2] += 1
        else:
            counts["unknown"] += 1
    return dict(counts)


def spatial_density_by_type(objects: Iterable[Oggetto]) -> dict[str, int]:
    counts: dict[str, int] = Counter()
    for obj in objects:
        counts[obj.tipo] += 1
    return dict(counts)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def radius_summary(
    objects: Iterable[Oggetto],
    center_lat: float,
    center_lon: float,
    radius_m: float,
) -> dict[str, int]:
    by_type: dict[str, int] = Counter()
    for obj in objects:
        d = _haversine_m(center_lat, center_lon, obj.posizione.lat, obj.posizione.lon)
        if d <= radius_m:
            by_type[obj.tipo] += 1
    return dict(by_type)


def temporal_field_trend(
    obj: Oggetto,
    field: str,
    hours: float = 1.0,
) -> list[tuple[datetime, float]]:
    cutoff = _utcnow().timestamp() - hours * 3600.0
    out: list[tuple[datetime, float]] = []
    for stato in obj.cronologia:
        if stato.t.timestamp() >= cutoff:
            val = stato.campi.get(field)
            if isinstance(val, (int, float)):
                out.append((stato.t, float(val)))
    return out


def latest_state_by_object(objects: Iterable[Oggetto]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for obj in objects:
        latest: dict[str, Any] = {}
        if obj.cronologia:
            last = obj.cronologia[-1]
            latest = dict(last.campi)
            latest["t"] = last.t
        else:
            latest = dict(obj.proprieta)
            latest["t"] = _utcnow()
        out[obj.id] = latest
    return out


def h3_grid_aggregation(
    objects: Iterable[Oggetto],
    resolution: int = 9,
) -> dict[str, dict[str, int]]:
    try:
        import h3
    except ImportError as exc:
        raise RuntimeError("h3 package required for H3 aggregation") from exc

    grid: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for obj in objects:
        idx = h3.latlng_to_cell(obj.posizione.lat, obj.posizione.lon, resolution)
        grid[idx][obj.tipo] += 1
    return {k: dict(v) for k, v in grid.items()}


def objects_in_timerange(
    objects: Iterable[Oggetto],
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Oggetto]:
    if start is None:
        start = datetime.min.replace(tzinfo=UTC)
    if end is None:
        end = _utcnow()
    out: list[Oggetto] = []
    for obj in objects:
        times = [s.t for s in obj.cronologia]
        if times and any(start <= t <= end for t in times) or not times:
            out.append(obj)
    return out
