"""Power analytics calculator."""

from __future__ import annotations

from ....core.models import Ride


def normalized_power_approx(ride: Ride) -> float:
    """Calculate Normalized Power from GPS power data or fallback approximation.

    True NP = (sum(P1^4, P2^4, ...)/n)^(1/4) for power meter data.
    Falls back to HR-based estimate if no power data available.
    """
    if ride.gps_points:
        power_values = [p.power for p in ride.gps_points if p.power is not None]
        if len(power_values) >= 10:
            np = (sum(p**4 for p in power_values) / len(power_values)) ** 0.25
            return round(max(0.0, np), 1)

    if ride.heart_rate_avg and ride.avg_speed_kmh:
        intensity = min(ride.avg_speed_kmh / 30.0, 1.0)
        hr_factor = min(ride.heart_rate_avg / 165.0, 1.0)
        return max(0.0, intensity * hr_factor * 250.0)

    return 0.0


def intensity_factor(ride: Ride, ftp: float = 250.0) -> float:
    np = normalized_power_approx(ride)
    if not np or ftp <= 0:
        return 0.0
    return min(np / ftp, 1.0)


def training_stress_score(ride: Ride, ftp: float = 250.0) -> float:
    hours = ride.duration_hours
    if hours <= 0:
        return 0.0
    if_ = intensity_factor(ride, ftp)
    if if_ <= 0:
        return 0.0
    tss = hours * 100.0 * (if_ ** 2)
    return round(min(tss, 500.0), 1)
