"""Budget-limited POI enrichment from SerpApi into the map database.

MVP bridge that turns SerpApi "local results" into persisted ``pois`` rows,
so the map database is progressively enriched while staying within the free
SerpApi monthly quota.

Design notes (MVP):
* A tiny ``serpapi_usage`` table (created lazily) tracks searches per calendar
  month so we never exceed ``settings.serpapi_monthly_budget``.
* Results are de-duplicated against existing nearby POIs (name + distance).
* Enriched POIs are tagged ``source:serpapi`` and ``category:<raw>`` so they
  can be identified later; no schema change is required.

Not included in the MVP (future iterations): S2/H3 coverage grid to avoid
re-searching the same area, and automatic triggering on ride import.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..db import database as db
from ..settings import get_settings
from ..utils.logger import get_logger
from . import serpapi_maps

logger = get_logger(__name__)

# Map raw SerpApi/Google place categories onto the app's constrained POI types
# (see api/schemas.py: POI_TYPES). Unknown categories default to "ristoro".
_CATEGORY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("fountain", "fontana"),
    ("water", "fontana"),
    ("viewpoint", "vista"),
    ("scenic", "vista"),
    ("lookout", "vista"),
    ("museum", "culturale"),
    ("monument", "culturale"),
    ("church", "culturale"),
    ("castle", "culturale"),
    ("historic", "culturale"),
    ("bike", "tecnico"),
    ("bicycle", "tecnico"),
    ("repair", "tecnico"),
    ("cafe", "ristoro"),
    ("coffee", "ristoro"),
    ("bakery", "ristoro"),
    ("restaurant", "ristoro"),
    ("bar", "ristoro"),
    ("food", "ristoro"),
)
_DEFAULT_POI_TYPE = "ristoro"


def _current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _ensure_usage_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS serpapi_usage (
            month TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )"""
    )


def get_usage(month: str | None = None) -> int:
    """Return the number of SerpApi searches recorded for ``month`` (YYYY-MM)."""
    month = month or _current_month()
    with db.get_db_connection() as conn:
        _ensure_usage_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT count FROM serpapi_usage WHERE month = ?", (month,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_remaining_budget(month: str | None = None) -> int:
    """Return remaining SerpApi searches for the current (or given) month."""
    budget = int(get_settings().serpapi_monthly_budget)
    return max(0, budget - get_usage(month))


def _record_call(month: str | None = None, n: int = 1) -> None:
    month = month or _current_month()
    with db.get_db_connection() as conn:
        _ensure_usage_table(conn)
        conn.execute(
            """INSERT INTO serpapi_usage (month, count) VALUES (?, ?)
            ON CONFLICT(month) DO UPDATE SET count = count + excluded.count""",
            (month, n),
        )
        conn.commit()


def _map_category(*fields: Any) -> tuple[str, str]:
    """Return (poi_type, raw_category) from arbitrary SerpApi category fields."""
    parts: list[str] = []
    for field in fields:
        if isinstance(field, str):
            parts.append(field)
        elif isinstance(field, (list, tuple)):
            parts.extend(str(x) for x in field)
    raw = ", ".join(p for p in parts if p).strip()
    haystack = raw.lower()
    for keyword, poi_type in _CATEGORY_KEYWORDS:
        if keyword in haystack:
            return poi_type, raw
    return _DEFAULT_POI_TYPE, raw


def _extract_coords(item: dict) -> tuple[float, float] | None:
    gps = item.get("gps_coordinates") or item.get("coordinates") or {}
    if isinstance(gps, dict):
        lat = gps.get("latitude", gps.get("lat"))
        lon = gps.get("longitude", gps.get("lng", gps.get("lon")))
    else:
        lat = item.get("latitude", item.get("lat"))
        lon = item.get("longitude", item.get("lon"))
    try:
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _extract_poi(item: dict, tenant_id: int, created_by: int | None) -> dict | None:
    if not isinstance(item, dict):
        return None
    name = (item.get("title") or item.get("name") or "").strip()
    coords = _extract_coords(item)
    if not name or coords is None:
        return None
    lat, lon = coords
    poi_type, raw_category = _map_category(item.get("type"), item.get("types"), item.get("category"))
    description = (item.get("address") or item.get("description") or raw_category or name).strip()
    tags = ["source:serpapi"]
    if raw_category:
        tags.append(f"category:{raw_category}")
    return {
        "name": name,
        "description": description,
        "lat": lat,
        "lon": lon,
        "type": poi_type,
        "photos": [],
        "tags": tags,
        "created_by": created_by,
        "tenant_id": tenant_id,
    }


def _is_duplicate(name: str, lat: float, lon: float, radius_m: float, tenant_id: int | None = None) -> bool:
    existing = db.get_nearby_pois(lat, lon, radius_km=max(0.0, radius_m) / 1000.0, tenant_id=tenant_id)
    target = name.strip().lower()
    return any((p.get("name") or "").strip().lower() == target for p in existing)


def enrich_pois_near(
    lat: float,
    lon: float,
    query: str = "cafe,bakery,restaurant",
    tenant_id: int = 0,
    created_by: int | None = None,
    dedup_radius_m: float = 120.0,
) -> dict[str, Any]:
    """Fetch nearby places from SerpApi and persist new POIs (budget-limited).

    Consumes at most one SerpApi search from the monthly budget. Returns a
    summary dict describing the outcome.
    """
    summary: dict[str, Any] = {
        "queried": False,
        "saved": 0,
        "skipped_duplicates": 0,
        "skipped_invalid": 0,
        "budget_remaining": get_remaining_budget(),
        "budget_exhausted": False,
    }

    if not serpapi_maps.get_serpapi_api_key():
        summary["reason"] = "no_api_key"
        return summary

    if summary["budget_remaining"] <= 0:
        summary["budget_exhausted"] = True
        summary["reason"] = "budget_exhausted"
        return summary

    data = serpapi_maps.search_places(query, lat, lon)
    # A request was attempted against the API key, so it counts toward quota.
    _record_call()
    summary["queried"] = True
    summary["budget_remaining"] = get_remaining_budget()

    results = []
    if data:
        results = data.get("local_results") or data.get("places_results") or []
    if not results:
        summary["reason"] = "no_results"
        return summary

    for item in results:
        poi = _extract_poi(item, tenant_id, created_by)
        if poi is None:
            summary["skipped_invalid"] += 1
            continue
        if _is_duplicate(poi["name"], poi["lat"], poi["lon"], dedup_radius_m, tenant_id=tenant_id):
            summary["skipped_duplicates"] += 1
            continue
        try:
            db.save_poi(poi)
            summary["saved"] += 1
        except Exception:  # noqa: BLE001 - never let one bad row abort the batch
            logger.warning("Failed to save enriched POI '%s'", poi.get("name"), exc_info=True)
            summary["skipped_invalid"] += 1

    logger.info(
        "SerpApi enrichment near (%s, %s): saved=%d dupes=%d invalid=%d budget_left=%d",
        lat,
        lon,
        summary["saved"],
        summary["skipped_duplicates"],
        summary["skipped_invalid"],
        summary["budget_remaining"],
    )
    return summary


__all__ = [
    "enrich_pois_near",
    "get_usage",
    "get_remaining_budget",
]
