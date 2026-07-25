"""Aggregate time-in-zone distributions for an athlete.

Builds power-zone and heart-rate-zone *distributions* (percentage of
training time spent in each zone) across all of an athlete's rides, using the
per-sample ``gps_points`` already stored on each ride. This powers the
frontend "Training Zones" charts and reuses the canonical zone math from
:mod:`power_model` and :mod:`advanced`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.models import GPSPoint
from .advanced import calculate_heart_rate_zones
from .power_model import POWER_ZONES_COGGAN, calculate_power_zones

# Heart-rate zone boundaries as % of max HR (Coggan 5-zone model).
HR_ZONE_PCT = [
    ("Z1", "Recovery", 0.55, 0.64, "#4ecca3"),
    ("Z2", "Endurance", 0.64, 0.74, "#90EE90"),
    ("Z3", "Tempo", 0.74, 0.84, "#FFD700"),
    ("Z4", "Threshold", 0.84, 0.94, "#FFA500"),
    ("Z5", "VO2max", 0.94, 1.01, "#FF4500"),
]

DEFAULT_MAX_HR = 190
DEFAULT_FTP = 250.0


@dataclass
class ZoneDistribution:
    """Time-in-zone distribution for a single metric."""

    metric: str
    available: bool
    total_samples: int
    zones: list[dict[str, Any]]


def _to_gps_points(gps_points: Any) -> list[GPSPoint]:
    """Coerce a ride's stored ``gps_points`` (list of dicts) into GPSPoint.

    Samples that lack a usable ``power``/``heart_rate`` are kept but those
    fields default to ``None`` so zone counters simply skip them.
    """
    if not gps_points:
        return []
    points: list[GPSPoint] = []
    for p in gps_points:
        if not isinstance(p, dict):
            continue
        points.append(
            GPSPoint(
                lat=float(p.get("lat", 0.0)),
                lon=float(p.get("lon", 0.0)),
                timestamp=str(p.get("timestamp", "")),
                power=_as_float(p.get("power")),
                heart_rate=_as_float(p.get("heart_rate")),
            )
        )
    return points


def _as_float(value: Any) -> float | None:
    """Converte ``value`` in float, ritornando None se assente o non numerico."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hr_distribution(
    hr_samples: list[float], max_hr: float
) -> list[dict[str, Any]]:
    """Conteggia i sample HR in ciascuna delle 5 zone Coggan (%HRmax).

    Per ogni zona conta i sample con ``lo <= hr < hi`` (Z5 inclusiva di max HR:
    ``lo <= hr <= hi``) e ne calcola la percentuale sul totale dei sample.
    """
    total = len(hr_samples)
    zones: list[dict[str, Any]] = []
    if total == 0:
        for name, label, low, high, color in HR_ZONE_PCT:
            lo = low * max_hr
            hi = high * max_hr
            zones.append(
                {
                    "zone": name,
                    "label": label,
                    "lower_bpm": round(lo, 0),
                    "upper_bpm": round(hi, 0),
                    "count": 0,
                    "pct_time": 0.0,
                    "color": color,
                }
            )
        return zones
    for name, label, low, high, color in HR_ZONE_PCT:
        lo = low * max_hr
        hi = high * max_hr
        count = sum(1 for h in hr_samples if lo <= h < hi) if name != "Z5" else sum(
            1 for h in hr_samples if lo <= h <= hi
        )
        zones.append(
            {
                "zone": name,
                "label": label,
                "lower_bpm": round(lo, 0),
                "upper_bpm": round(hi, 0),
                "count": count,
                "pct_time": round(count / total * 100, 1),
                "color": color,
            }
        )
    return zones


def calculate_zone_distributions(
    rides: list[dict[str, Any]],
    ftp_watts: float | None = None,
    max_hr: float | None = None,
) -> dict[str, Any]:
    """Aggregate power & HR time-in-zone distributions across ``rides``.

    Args:
        rides: list of ride dicts as returned by ``get_rides_by_athlete``
            (each may carry a parsed ``gps_points`` list).
        ftp_watts: athlete FTP in watts (drives power zones). Falls back to
            :data:`DEFAULT_FTP` when missing.
        max_hr: athlete maximum heart rate in bpm (drives HR zones).
            Falls back to :data:`DEFAULT_MAX_HR` when missing.

    Returns:
        Dict with ``power`` and ``hr`` :class:`ZoneDistribution`-shaped
        payloads plus the effective ``ftp_watts``/``max_hr`` used.
    """
    ftp = float(ftp_watts) if ftp_watts else DEFAULT_FTP
    mhr = float(max_hr) if max_hr else DEFAULT_MAX_HR

    power_points: list[GPSPoint] = []
    hr_samples: list[float] = []
    rides_with_power = 0
    rides_with_hr = 0

    for ride in rides:
        gps = ride.get("gps_points")
        if not gps:
            continue
        pts = _to_gps_points(gps)
        has_power = any(p.power is not None for p in pts)
        has_hr = any(p.heart_rate is not None for p in pts)
        if has_power:
            rides_with_power += 1
            power_points.extend(pts)
        if has_hr:
            rides_with_hr += 1
            hr_samples.extend(
                p.heart_rate for p in pts if p.heart_rate is not None
            )

    power_zones: list[dict[str, Any]] = []
    power_available = False
    if power_points:
        raw = calculate_power_zones(power_points, ftp)
        power_available = bool(raw)
        for name, label, _low, _high, color in POWER_ZONES_COGGAN:
            z = raw.get(name, {})
            power_zones.append(
                {
                    "zone": name,
                    "label": label,
                    "lower_w": z.get("lower_w"),
                    "upper_w": z.get("upper_w"),
                    "count": z.get("count", 0),
                    "pct_time": z.get("pct_time", 0.0),
                    "color": color,
                }
            )

    hr_zones = _hr_distribution(hr_samples, mhr)
    hr_available = bool(hr_samples)

    return {
        "ftp_watts": round(ftp, 0),
        "max_hr": round(mhr, 0),
        "rides_with_power": rides_with_power,
        "rides_with_hr": rides_with_hr,
        "power": {
            "metric": "power",
            "available": power_available,
            "total_samples": len(power_points),
            "zones": power_zones,
        },
        "hr": {
            "metric": "hr",
            "available": hr_available,
            "total_samples": len(hr_samples),
            "zones": hr_zones,
        },
        # Backwards-compatible helpers used by the legacy HR-zone endpoint.
        "hr_zone_reference": calculate_heart_rate_zones(max_hr=int(mhr)),
    }