"""Training Stress Score (TSS) and exponentially weighted moving average."""

from __future__ import annotations

from .error_propagation import ErrorValue


def exponentially_weighted_moving_average(values: list[float], tau_days: float) -> float:
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
    result = estimate_tss_with_error(ride, ftp)
    return round(result.value, 1)


def estimate_tss_with_error(ride, ftp: float = 250.0) -> ErrorValue:
    """Estimate TSS with statistical and resolution error."""
    duration_h = ride.duration_hours
    if duration_h <= 0:
        return ErrorValue(value=0.0, stat_error=0.0, coverage=0.0)

    intensity_factor = 0.5
    if hasattr(ride, "intensity_factor") and ride.intensity_factor:
        intensity_factor = ride.intensity_factor
    elif ride.avg_speed_kmh and ride.avg_speed_kmh > 0:
        intensity_factor = min(ride.avg_speed_kmh / 40.0, 1.0)

    tss_value = duration_h * 100 * (intensity_factor**2)
    tss_value = min(tss_value, 500.0)

    coverage = 1.0
    if not ride.duration_minutes:
        coverage -= 0.3
    if not ride.avg_speed_kmh:
        coverage -= 0.3
    if not hasattr(ride, "intensity_factor") or not ride.intensity_factor:
        coverage -= 0.2
    coverage = max(0.0, coverage)

    base_stat_error = 0.2
    if coverage < 1.0:
        base_stat_error *= (2.0 - coverage)
    base_stat_error = min(base_stat_error, 1.0)

    return ErrorValue(
        value=round(tss_value, 1),
        stat_error=round(base_stat_error, 4),
        resolution_error=0.5,
        coverage=coverage,
    )


__all__ = ["estimate_tss", "estimate_tss_with_error", "exponentially_weighted_moving_average"]
