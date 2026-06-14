"""Route safety analyzer based on road types, bike infrastructure, and incidents."""

from __future__ import annotations

from typing import Any

_ROAD_SAFETY_WEIGHTS: dict[str, float] = {
    "cycleway": 0.9,
    "pedestrian": 0.85,
    "living_street": 0.75,
    "residential": 0.65,
    "unclassified": 0.55,
    "tertiary": 0.5,
    "secondary": 0.4,
    "primary": 0.3,
    "trunk": 0.2,
    "motorway": 0.05,
    "unknown": 0.4,
}

_BIKE_INFRASTRUCTURE_BONUS = 0.15
_INCIDENT_PENALTY_PER_KM = 0.02


def compute_risk_score(
    road_types: dict[str, int],
    has_bike_infra: bool = False,
    incident_count: int = 0,
    route_length_km: float = 1.0,
) -> dict[str, Any]:
    """Compute a route risk score (0-1, higher = safer) and breakdown."""
    if not road_types:
        road_types = {"residential": 1}
    total = sum(road_types.values())
    weighted_sum = sum(_ROAD_SAFETY_WEIGHTS.get(rt, 0.4) * cnt for rt, cnt in road_types.items())
    base_score = weighted_sum / total if total > 0 else 0.4
    if has_bike_infra:
        base_score = min(1.0, base_score + _BIKE_INFRASTRUCTURE_BONUS)
    incident_penalty = min(
        0.4,
        incident_count * _INCIDENT_PENALTY_PER_KM * (incident_count / max(route_length_km, 0.1)),
    )
    final_score = max(0.0, min(1.0, base_score - incident_penalty))
    if final_score >= 0.7:
        label = "low_risk"
        advice = "Percorso sicuro"
    elif final_score >= 0.45:
        label = "medium_risk"
        advice = "Attenzione: alcune strade pericolose"
    else:
        label = "high_risk"
        advice = "Rischio elevato: evita se possibile"
    return {
        "risk_score": round(final_score, 2),
        "label": label,
        "advice": advice,
        "base_score": round(base_score, 2),
        "incident_penalty": round(incident_penalty, 3),
        "dominant_road_types": sorted(road_types.items(), key=lambda x: x[1], reverse=True)[:5],
    }


async def analyze_route_safety(
    gps_points: list[dict[str, float]],
    incidents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full safety analysis for a route given GPS points and optional incident data."""
    from .overpass_client import fetch_bike_lanes, get_road_type_summary

    road_types = await get_road_type_summary(gps_points)
    bike_data = await fetch_bike_lanes(gps_points)
    has_bike_infra = bool(bike_data and bike_data.get("elements"))
    incident_count = len(incidents) if incidents else 0
    lats = [p["lat"] for p in gps_points]
    lons = [p["lon"] for p in gps_points]
    from math import asin, cos, radians, sin, sqrt

    route_length_km = 0.0
    for i in range(len(gps_points) - 1):
        lat1, lon1 = radians(lats[i]), radians(lons[i])
        lat2, lon2 = radians(lats[i + 1]), radians(lons[i + 1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        route_length_km += 2 * 6371 * asin(sqrt(a))
    if route_length_km < 0.01:
        route_length_km = 1.0
    score = compute_risk_score(road_types, has_bike_infra, incident_count, route_length_km)
    score["has_bike_infrastructure"] = has_bike_infra
    score["route_length_km"] = round(route_length_km, 2)
    score["incident_count"] = incident_count
    score["road_type_counts"] = road_types
    return score
