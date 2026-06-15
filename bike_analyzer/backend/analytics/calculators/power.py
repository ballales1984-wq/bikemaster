"""Power analytics calculator."""

from __future__ import annotations

from ....core.models import Ride


def normalized_power_approx(ride: Ride) -> float:
    if not ride.avg_speed_kmh:
        return 0.0
    return max(0.0, ride.avg_speed_kmh * 4.5)


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
    tss = hours * 100.0 * (if_ ** 2)
    return round(min(tss, 500.0), 1)
