"""Anomaly detection for cycling rides.

Detects statistical outliers and unusual patterns in ride data:
- Distance outliers
- Duration outliers
- Speed outliers
- Elevation gain outliers
- Calorie outliers
- Combined anomaly scores
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.models import Ride


@dataclass
class AnomalyResult:
    metric: str
    value: float
    mean: float
    std: float
    z_score: float
    is_anomaly: bool
    severity: str


@dataclass
class RideAnomalyReport:
    ride_id: int | None
    date: str
    anomalies: list[AnomalyResult]
    anomaly_score: float
    risk_level: str


def _z_score(value: float, mean: float, std: float) -> float:
    """Calculates the z-score (deviation from mean in standard deviation units).

    Returns 0 when standard deviation is zero (degenerate distribution) to
    evitare divisione per zero.
    """
    if std <= 0:
        return 0.0
    return (value - mean) / std


def detect_ride_anomalies(
    rides: list[Ride],
    z_threshold: float = 2.5,
) -> list[RideAnomalyReport]:
    """Detect statistical anomalies in a list of rides.

    Uses z-score method: values beyond `z_threshold` standard deviations
    from the mean are flagged as anomalies.

    Args:
        rides: List of Ride objects to analyze.
        z_threshold: Number of standard deviations for anomaly threshold.

    Returns:
        List of RideAnomalyReport with per-ride anomaly details.
    """
    if not rides or len(rides) < 3:
        return []

    metrics = {
        "distance_km": [r.distance_km for r in rides],
        "duration_minutes": [r.duration_minutes for r in rides],
        "avg_speed_kmh": [r.avg_speed_kmh for r in rides],
        "elevation_gain_m": [r.elevation_gain_m or 0 for r in rides],
        "calories": [r.calories for r in rides],
    }

    stats: dict[str, dict[str, float]] = {}
    for name, values in metrics.items():
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        stats[name] = {"mean": mean, "std": std}

    severity_map = {
        "distance_km": ("low", "Unusually long or short ride"),
        "duration_minutes": ("low", "Unusually long or short duration"),
        "avg_speed_kmh": ("medium", "Unusually fast or slow speed"),
        "elevation_gain_m": ("medium", "Unusual elevation profile"),
        "calories": ("high", "Unusual calorie expenditure"),
    }

    reports: list[RideAnomalyReport] = []
    for ride in rides:
        anomalies: list[AnomalyResult] = []
        for metric_name, stat in stats.items():
            value = float(getattr(ride, metric_name) or 0)
            z = _z_score(value, stat["mean"], stat["std"])
            if abs(z) >= z_threshold:
                sev, desc = severity_map.get(metric_name, ("low", "Anomalous value"))
                anomalies.append(
                    AnomalyResult(
                        metric=metric_name,
                        value=round(value, 2),
                        mean=round(stat["mean"], 2),
                        std=round(stat["std"], 2),
                        z_score=round(z, 2),
                        is_anomaly=True,
                        severity=sev,
                    )
                )

        score = sum(1.0 / (abs(a.z_score) + 0.1) for a in anomalies)
        risk = _risk_level(score, len(anomalies))
        reports.append(
            RideAnomalyReport(
                ride_id=ride.id,
                date=ride.date[:10] if ride.date else "",
                anomalies=anomalies,
                anomaly_score=round(score, 2),
                risk_level=risk,
            )
        )

    return reports


def _risk_level(score: float, anomaly_count: int) -> str:
    """Mappa anomalie → livello di rischio.

    high se >=3 metriche anomale o score>=5; medium se >=2 o score>=2;
    low if >=1; none otherwise. Score is sum of 1/(|z|+0.1), so
    premia molte anomalie con z-score moderato.
    """
    if anomaly_count >= 3 or score >= 5:
        return "high"
    if anomaly_count >= 2 or score >= 2:
        return "medium"
    if anomaly_count >= 1:
        return "low"
    return "none"


def summarize_anomalies(reports: list[RideAnomalyReport]) -> dict[str, Any]:
    """Aggregate anomaly reports into summary statistics.

    Args:
        reports: List of per-ride anomaly reports.

    Returns:
        Summary dict with counts, distribution, and flagged rides.
    """
    if not reports:
        return {
            "total_rides": 0,
            "anomalous_rides": 0,
            "risk_distribution": {"high": 0, "medium": 0, "low": 0, "none": 0},
            "flagged_rides": [],
        }

    distribution: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "none": 0}
    flagged: list[dict[str, Any]] = []

    for report in reports:
        distribution[report.risk_level] = distribution.get(report.risk_level, 0) + 1
        if report.risk_level in ("high", "medium", "low"):
            flagged.append(
                {
                    "ride_id": report.ride_id,
                    "date": report.date,
                    "risk_level": report.risk_level,
                    "anomaly_score": report.anomaly_score,
                    "anomalies": [
                        {
                            "metric": a.metric,
                            "value": a.value,
                            "z_score": a.z_score,
                            "severity": a.severity,
                        }
                        for a in report.anomalies
                    ],
                }
            )

    return {
        "total_rides": len(reports),
        "anomalous_rides": sum(1 for r in reports if r.risk_level in ("high", "medium", "low")),
        "risk_distribution": distribution,
        "flagged_rides": flagged,
    }


__all__ = [
    "AnomalyResult",
    "RideAnomalyReport",
    "detect_ride_anomalies",
    "summarize_anomalies",
]

