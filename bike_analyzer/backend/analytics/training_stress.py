"""Training Stress Score (TSS) and exponentially weighted moving average."""
from __future__ import annotations
from typing import List

from .training_load import TrainingLoadDay


def exponentially_weighted_moving_average(values: List[float], tau_days: float) -> float:
    """Exponentially weighted moving average (EWMA) for training stress.

    Uses decay factor alpha = 1 - exp(-1/tau) applied iteratively.
    """
    if not values:
        return 0.0
    alpha = 1.0 - 2.718281828459045 ** (-1.0 / tau_days)
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1.0 - alpha) * result
    return round(result, 1)


def estimate_tss(ride, ftp: float = 250.0) -> float:
    """Estimate Training Stress Score for a ride.

    TSS = (duration_s * NP * IF) / (FTP * 3600) * 100
    Simplified: uses normalized power approximation from avg_speed and intensity.
    """
    duration_h = ride.duration_hours
    if duration_h <= 0:
        return 0.0

    intensity_factor = 0.5
    if hasattr(ride, "intensity_factor") and ride.intensity_factor:
        intensity_factor = ride.intensity_factor
    elif ride.avg_speed_kmh and ride.avg_speed_kmh > 0:
        intensity_factor = min(ride.avg_speed_kmh / 40.0, 1.0)

    tss = duration_h * 100 * (intensity_factor ** 2)
    return round(min(tss, 500.0), 1)


__all__ = ["estimate_tss", "exponentially_weighted_moving_average"]
