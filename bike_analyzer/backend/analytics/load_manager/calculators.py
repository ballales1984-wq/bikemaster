"""Load Manager — pure calculation functions.

Spec (agent): "Pure functions: calculate_tss(), calculate_ewma(), calculate_acwr()".
All functions are deterministic and side-effect free.
"""

from __future__ import annotations

from math import exp

from .config import LoadManagerConfig, DEFAULT_CONFIG


def calculate_tss(
    duration_hours: float,
    intensity_factor: float,
    ftp_watts: float | None = None,
    normalized_power: float | None = None,
    avg_power: float | None = None,
    terrain_correction: float = 0.0,
    cap: float = 500.0,
) -> dict:
    """Training Stress Score for a single ride.

    Formula: TSS = IF^2 * duration(h) * 100, with an optional terrain correction
    that increases TSS on climbing rides (agent: "salita aumenta TSS").

    When power data is available the caller should pass ``intensity_factor = NP/FTP``
    and ``normalized_power``; otherwise IF is estimated from HR/speed upstream.
    """
    if duration_hours <= 0 or intensity_factor <= 0:
        return {
            "tss": 0.0,
            "intensity_factor": 0.0,
            "normalized_power": normalized_power,
            "avg_power": avg_power,
            "terrain_correction": terrain_correction,
        }

    tss = (intensity_factor**2) * duration_hours * 100.0
    tss *= 1.0 + terrain_correction
    return {
        "tss": round(min(tss, cap), 1),
        "intensity_factor": round(intensity_factor, 3),
        "normalized_power": round(normalized_power, 1) if normalized_power is not None else None,
        "avg_power": round(avg_power, 1) if avg_power is not None else None,
        "terrain_correction": round(terrain_correction, 3),
    }


def calculate_ewma(values: list[float], tau_days: float) -> list[float]:
    """Exponentially weighted moving average series.

    Iterative recurrence with alpha = 1 - exp(-1/tau). Returns one value per input.
    """
    if not values:
        return []
    alpha = 1.0 - exp(-1.0 / max(tau_days, 1e-9))
    out: list[float] = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1.0 - alpha) * out[-1])
    return [round(x, 1) for x in out]


def calculate_acwr(
    short_window_tss: list[float],
    long_window_tss: list[float],
) -> float:
    """Acute:Chronic Workload Ratio.

    ACWR = mean(short_window) / mean(long_window).
    The agent defines short = 7 days, long = 28 days (treated as windows of sums
    or mean-equivalent; using raw means keeps the ratio window-size invariant).
    """
    if not short_window_tss or not long_window_tss:
        return 0.0
    short_mean = sum(short_window_tss) / len(short_window_tss)
    long_mean = sum(long_window_tss) / len(long_window_tss)
    if long_mean <= 0:
        return 0.0
    return round(short_mean / long_mean, 3)


def terrain_correction(elevation_gain_m: float | None, distance_km: float | None) -> float:
    """Climbing correction factor in [0, 0.3].

    ~ +1% TSS per 100 m/km of gradient, capped at +30%.
    """
    if not elevation_gain_m or not distance_km or distance_km <= 0:
        return 0.0
    gradient = elevation_gain_m / distance_km
    return round(min(gradient / 100.0, 0.3), 3)


__all__ = [
    "calculate_tss",
    "calculate_ewma",
    "calculate_acwr",
    "terrain_correction",
]
