"""Power analytics calculator.

Computes Normalized Power, Intensity Factor, and Training Stress Score
from ride data. NP uses the fourth-power mean of power samples; IF and TSS
normalize against the athlete's Functional Threshold Power (FTP).
"""

from __future__ import annotations

from ..models import Ride


def normalized_power_approx(ride: Ride) -> float:
    """Calculate Normalized Power from GPS power data or fallback approximation.

    True NP = (mean(P^4))^(1/4) for power meter data (requires >= 10 samples).
    Falls back to an HR+speed-based estimate when no power meter data exists:
    NP ~= intensity * hr_factor * 250W.

    Args:
        ride: Cycling activity with optional gps_points (power) and heart_rate_avg.

    Returns:
        Normalized Power in watts, or 0.0 if insufficient data.
    """
    if ride.gps_points:
        power_values = [p.power for p in ride.gps_points if p.power is not None]
        if len(power_values) >= 10:
            # Fourth-power mean gives more weight to high-power efforts,
            # which is the standard NP algorithm (Allen & Coggan).
            np = (sum(p**4 for p in power_values) / len(power_values)) ** 0.25
            return round(max(0.0, np), 1)

    if ride.heart_rate_avg and ride.avg_speed_kmh:
        intensity = min(ride.avg_speed_kmh / 30.0, 1.0)
        hr_factor = min(ride.heart_rate_avg / 165.0, 1.0)
        return max(0.0, intensity * hr_factor * 250.0)

    return 0.0


def intensity_factor(ride: Ride, ftp: float = 250.0) -> float:
    """Intensity Factor (IF): NP / FTP.

    Indicates the relative intensity of the ride compared to the athlete's
    threshold. IF > 1.0 means the ride was harder than FTP.

    Args:
        ride: Cycling activity.
        ftp: Functional Threshold Power in watts.

    Returns:
        Intensity Factor (0.0 to 1.0+), or 0.0 if no NP or FTP.
    """
    np = normalized_power_approx(ride)
    if not np or ftp <= 0:
        return 0.0
    return min(np / ftp, 1.0)


def training_stress_score(ride: Ride, ftp: float = 250.0) -> float:
    """Training Stress Score (TSS): IF^2 * duration(h) * 100.

    Standard Banister/Coggin model: TSS scales with the square of intensity
    (IF) and linearly with duration. Clamped to 500 to prevent outlier
    inflation from extreme rides.

    Args:
        ride: Cycling activity.
        ftp: Functional Threshold Power in watts.

    Returns:
        TSS value rounded to 1 decimal, max 500.0.
    """
    hours = ride.duration_hours
    if hours <= 0:
        return 0.0
    if_ = intensity_factor(ride, ftp)
    if if_ <= 0:
        return 0.0
    tss = hours * 100.0 * (if_**2)
    return round(min(tss, 500.0), 1)
