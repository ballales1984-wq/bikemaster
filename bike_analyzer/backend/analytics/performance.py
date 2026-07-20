"""Performance Engine: Scoring system for cycling performance."""

from __future__ import annotations

import math

from ..models.models import AthleteProfile, Ride
from .fatigue import calculate_fatigue_score
from .error_propagation import ErrorValue, combine_errors_quadrature, propagate_division, propagate_multiplication, compute_coverage


def calculate_performance_score(ride: Ride) -> float:
    """Performance score (0-10) of a single ride.

    Combines speed (40%), duration (40%) and elevation (20%) normalized on
    thresholds (30 km/h, 2 h, 500 m), then scaled to 10. Rewards fast,
    long rides with climbs.
    """
    speed_factor = min(ride.avg_speed_kmh / 30.0, 1.0)
    duration_factor = min(ride.duration_hours / 2.0, 1.0)
    elevation_factor = min(ride.elevation_gain_m / 500.0, 1.0) if ride.elevation_gain_m else 0
    return round((speed_factor * 0.4 + duration_factor * 0.4 + elevation_factor * 0.2) * 10.0, 1)


def calculate_endurance_score(rides: list[Ride]) -> float:
    """Endurance score (0-10) over the athlete's entire history.

    Weight: proportion of "long" rides >=2h (40%), consistency in the number
    of rides (30%, saturates at 20) and total volume (30%, saturates at 500 km).
    """
    if not rides:
        return 0.0
    long_rides = sum(1 for r in rides if r.duration_hours >= 2.0)
    long_ride_ratio = long_rides / len(rides)
    consistency = min(len(rides) / 20.0, 1.0)
    total_distance = sum(r.distance_km for r in rides)
    distance_factor = min(total_distance / 500.0, 1.0)
    return round((long_ride_ratio * 0.4 + consistency * 0.3 + distance_factor * 0.3) * 10.0, 1)


def calculate_recovery_score(ride: Ride) -> float:
    """Recovery score (0-10): inverse of the fatigue of the same ride."""
    fatigue = calculate_fatigue_score(ride)
    return round(10.0 - fatigue, 1)


def calculate_efficiency_score(ride: Ride) -> float:
    """Energy efficiency (0-10): how few kcal/km compared to the benchmark.

    kcal/km below 30 (benchmark) gives 10; above, it decreases linearly by 1 point
    every 5 kcal/km in excess (clamp at 0). Fewer calories per km = more efficient.
    """
    if ride.distance_km <= 0:
        return 0.0
    calories_per_km = ride.calories / ride.distance_km
    benchmark = 30.0
    efficiency = max(0, min(10, 10 - (calories_per_km - benchmark) / 5.0))
    return round(efficiency, 1)


def calculate_monthly_scores(rides: list[Ride]) -> dict:
    if not rides:
        return {
            "performance": 0.0,
            "endurance": 0.0,
            "recovery": 0.0,
            "efficiency": 0.0,
            "avg_fatigue": 0.0,
        }

    return {
        "performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1),
        "endurance": calculate_endurance_score(rides),
        "recovery": round(sum(calculate_recovery_score(r) for r in rides) / len(rides), 1),
        "efficiency": round(sum(calculate_efficiency_score(r) for r in rides) / len(rides), 1),
        "avg_fatigue": round(sum(calculate_fatigue_score(r) for r in rides) / len(rides), 1),
    }


def calculate_annual_scores(rides: list[Ride]) -> dict:
    """Aggregates annual scores + totals (km, kcal, avg fatigue) over the history."""
    if not rides:
        return {
            "performance": 0,
            "endurance": 0,
            "total_km": 0,
            "total_calories": 0,
            "avg_fatigue": 0,
        }
    from .analytics import calculate_summary

    s = calculate_summary(rides)
    return {
        "performance": round(sum(calculate_performance_score(r) for r in rides) / len(rides), 1),
        "endurance": calculate_endurance_score(rides),
        "total_km": s["total_km"],
        "total_calories": s["total_calories"],
        "avg_fatigue": s["avg_fatigue"],
    }


def classify_athlete(rides: list[Ride]) -> str:
    """Classifies the athlete by volume (total km and number of rides) into 5 levels.

    Beginner → Amateur → Intermediate → Advanced → Elite, with increasing
    thresholds on km and number of rides.
    """
    if not rides:
        return "Unclassified"
    total_km = sum(r.distance_km for r in rides)
    total_rides = len(rides)
    if total_km < 100 and total_rides < 10:
        return "Beginner"
    if total_km < 500 and total_rides < 50:
        return "Amateur"
    if total_km < 1500 and total_rides < 150:
        return "Intermediate"
    if total_km < 3000:
        return "Advanced"
    return "Elite"


def get_experience_level(athlete: AthleteProfile) -> str:
    """Returns the experience level declared in the athlete profile."""
    return athlete.experience_level


def should_save_to_database(points: list) -> bool:
    """True if all GPS points pass validation (coordinates + timestamp)."""
    from ..processing.processing import validate_gps_point

    return all(validate_gps_point(p) for p in points) if points else False


def calculate_normalized_power(power_stream: list[float], rolling_s: int = 30) -> float | None:
    """Normalized Power (NP): mean of the 4th power over a 30s rolling window, to the 1/4.

    Requires a power stream (W) sampled at 1 Hz. If the stream is empty or
    flat (all equal values), returns None because NP is not defined.
    """
    result = calculate_normalized_power_with_error(power_stream, rolling_s)
    return result.value if result is not None else None


def calculate_normalized_power_with_error(power_stream: list[float], rolling_s: int = 30) -> ErrorValue | None:
    """Normalized Power con margine di errore statistico e di risoluzione."""
    if not power_stream or len(power_stream) < rolling_s:
        return None
    valid = [p for p in power_stream if p is not None and p >= 0]
    if not valid:
        return None

    rolling_avg: list[float] = []
    for i in range(len(valid)):
        window = valid[max(0, i - rolling_s + 1) : i + 1]
        rolling_avg.append(sum(window) / len(window))

    if not rolling_avg:
        return None
    mean_4th = sum(p**4 for p in rolling_avg) / len(rolling_avg)
    np_value = mean_4th**0.25

    stat_error = 0.0
    if len(valid) > 1:
        mean = sum(valid) / len(valid)
        variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1)
        stat_error = math.sqrt(variance) / math.sqrt(len(valid))

    coverage = compute_coverage(len(valid), len(power_stream))
    return ErrorValue(
        value=round(np_value, 1),
        stat_error=round(stat_error, 4),
        resolution_error=1.0,
        coverage=coverage,
    )


def calculate_intensity_factor(normalized_power: float | None, ftp: float | None) -> float | None:
    """Intensity Factor (IF): NP / FTP. None if FTP missing or invalid."""
    result = calculate_intensity_factor_with_error(normalized_power, ftp)
    return result.value if result is not None else None


def calculate_intensity_factor_with_error(
    normalized_power: float | None,
    ftp: float | None,
    np_error: ErrorValue | None = None,
    ftp_error: float = 0.0,
) -> ErrorValue | None:
    """Intensity Factor with error propagation from NP and FTP."""
    if not normalized_power or not ftp or ftp <= 0:
        return None
    if_value = normalized_power / ftp
    np_stat = np_error.stat_error if np_error else 0.0
    np_res = np_error.resolution_error if np_error else 0.0
    stat_error = propagate_division(normalized_power, np_stat, ftp, ftp_error).stat_error
    resolution_error = propagate_division(normalized_power, np_res, ftp, 0.0).stat_error
    return ErrorValue(
        value=round(if_value, 3),
        stat_error=round(stat_error, 6),
        resolution_error=round(resolution_error, 6),
        coverage=np_error.coverage if np_error else 1.0,
    )


def calculate_tss(
    normalized_power: float | None,
    ftp: float | None,
    duration_seconds: float | None,
    intensity_factor: float | None = None,
) -> float | None:
    """Training Stress Score: (sec * NP * IF) / (FTP * 3600) * 100.

    ACCEPTS pre-computed IF or derives it from NP/FTP. None if data missing.
    """
    result = calculate_tss_with_error(normalized_power, ftp, duration_seconds, intensity_factor)
    return result.value if result is not None else None


def calculate_tss_with_error(
    normalized_power: float | None,
    ftp: float | None,
    duration_seconds: float | None,
    intensity_factor: float | None = None,
    np_error: ErrorValue | None = None,
    ftp_error: float = 0.0,
    duration_error: float = 0.0,
) -> ErrorValue | None:
    """Training Stress Score with error propagation."""
    if duration_seconds is None or duration_seconds <= 0:
        return None
    if intensity_factor is None:
        intensity_factor = calculate_intensity_factor(normalized_power, ftp)
    if intensity_factor is None or not ftp or ftp <= 0:
        return None
    np_eff = normalized_power or (intensity_factor * ftp)
    tss_value = (duration_seconds * np_eff * intensity_factor) / (ftp * 3600.0) * 100.0

    np_stat = np_error.stat_error if np_error else 0.0
    np_res = np_error.resolution_error if np_error else 0.0
    if_stat = 0.01
    if_res = 0.005

    rel_np = np_stat / abs(np_eff) if np_eff != 0 else 0.0
    rel_if = if_stat / abs(intensity_factor) if intensity_factor != 0 else 0.0
    rel_ftp = ftp_error / abs(ftp) if ftp != 0 else 0.0
    rel_dur = duration_error / abs(duration_seconds) if duration_seconds != 0 else 0.0
    total_rel = math.sqrt(rel_np ** 2 + rel_if ** 2 + rel_ftp ** 2 + rel_dur ** 2)
    stat_error = abs(tss_value) * total_rel

    rel_np_r = np_res / abs(np_eff) if np_eff != 0 else 0.0
    rel_if_r = if_res / abs(intensity_factor) if intensity_factor != 0 else 0.0
    rel_ftp_r = 0.01
    rel_dur_r = duration_error / abs(duration_seconds) if duration_seconds != 0 else 0.0
    total_rel_r = math.sqrt(rel_np_r ** 2 + rel_if_r ** 2 + rel_ftp_r ** 2 + rel_dur_r ** 2)
    resolution_error = abs(tss_value) * total_rel_r

    coverage = np_error.coverage if np_error else 1.0
    return ErrorValue(
        value=round(tss_value, 1),
        stat_error=round(stat_error, 4),
        resolution_error=round(resolution_error, 4),
        coverage=coverage,
    )


def estimate_ftp_from_test(
    test_power: float,
    test_duration_min: float = 20.0,
    ftp_fraction: float = 0.95,
) -> float | None:
    """Estimate FTP from a threshold test.

    Default: average power over 20 min * 0.95 (standard 20-min FTP test).
    For a 60 min test use ftp_fraction=1.0; for 8 min use ~0.90.
    """
    result = estimate_ftp_from_test_with_error(test_power, test_duration_min, ftp_fraction)
    return result.value if result is not None else None


def estimate_ftp_from_test_with_error(
    test_power: float,
    test_duration_min: float = 20.0,
    ftp_fraction: float = 0.95,
) -> ErrorValue | None:
    """Stima FTP da test con margine di errore."""
    if not test_power or test_power <= 0:
        return None
    if test_duration_min <= 0:
        return None
    ftp_value = test_power * ftp_fraction
    stat_error = test_power * ftp_fraction * 0.05
    return ErrorValue(
        value=round(ftp_value, 1),
        stat_error=round(stat_error, 4),
        resolution_error=1.0,
        coverage=1.0,
    )


def estimate_ftp_from_ride(
    power_stream: list[float],
    duration_seconds: float | None = None,
    ftp_fraction: float = 0.95,
) -> float | None:
    """Estimate FTP from a ride: NP of the longest power zone * fraction.

    Simplified heuristic: uses the NP of the entire ride as a proxy for the
    threshold test and scales it with ftp_fraction. Returns None if the stream
    is insufficient.
    """
    result = estimate_ftp_from_ride_with_error(power_stream, duration_seconds, ftp_fraction)
    return result.value if result is not None else None


def estimate_ftp_from_ride_with_error(
    power_stream: list[float],
    duration_seconds: float | None = None,
    ftp_fraction: float = 0.95,
) -> ErrorValue | None:
    """Estimate FTP from ride with error margin."""
    if not duration_seconds or duration_seconds < 600:
        return None
    np_error = calculate_normalized_power_with_error(power_stream)
    if np_error is None:
        return None
    ftp_value = np_error.value * ftp_fraction
    stat_error = np_error.stat_error * ftp_fraction
    return ErrorValue(
        value=round(ftp_value, 1),
        stat_error=round(stat_error, 4),
        resolution_error=1.0,
        coverage=np_error.coverage,
    )


def calculate_power_metrics(
    power_stream: list[float],
    ftp: float | None,
    duration_seconds: float | None,
) -> dict:
    """Aggregates all power metrics for a ride into a single dict.

    Fields: average_power, normalized_power, intensity_factor, tss.
    Uncomputable fields are None.
    """
    result = calculate_power_metrics_with_error(power_stream, ftp, duration_seconds)
    return {
        "average_power": result["average_power"].value if result["average_power"] else None,
        "normalized_power": result["normalized_power"].value if result["normalized_power"] else None,
        "intensity_factor": result["intensity_factor"].value if result["intensity_factor"] else None,
        "tss": result["tss"].value if result["tss"] else None,
    }


def calculate_power_metrics_with_error(
    power_stream: list[float],
    ftp: float | None,
    duration_seconds: float | None,
    ftp_error: float = 0.0,
    duration_error: float = 0.0,
) -> dict:
    """Aggregates power metrics with error margins."""
    if not power_stream:
        return {
            "average_power": None,
            "normalized_power": None,
            "intensity_factor": None,
            "tss": None,
        }
    valid = [p for p in power_stream if p is not None and p >= 0]
    avg_value = round(sum(valid) / len(valid), 1) if valid else None
    mean = sum(valid) / len(valid) if valid else 0.0
    variance = sum((x - mean) ** 2 for x in valid) / (len(valid) - 1) if len(valid) > 1 else 0.0
    avg_stat_error = math.sqrt(variance) / math.sqrt(len(valid)) if valid else 0.0
    avg_coverage = compute_coverage(len(valid), len(power_stream))

    avg_ev = ErrorValue(
        value=avg_value if avg_value is not None else 0.0,
        stat_error=round(avg_stat_error, 4),
        resolution_error=1.0,
        coverage=avg_coverage,
    ) if avg_value is not None else None

    np_ev = calculate_normalized_power_with_error(power_stream)
    if_ev = calculate_intensity_factor_with_error(
        np_ev.value if np_ev else None,
        ftp,
        np_ev,
        ftp_error,
    )
    tss_ev = calculate_tss_with_error(
        np_ev.value if np_ev else None,
        ftp,
        duration_seconds,
        if_ev.value if if_ev else None,
        np_ev,
        ftp_error,
        duration_error,
    )

    return {
        "average_power": avg_ev,
        "normalized_power": np_ev,
        "intensity_factor": if_ev,
        "tss": tss_ev,
    }


__all__ = [
    "calculate_performance_score",
    "calculate_endurance_score",
    "calculate_recovery_score",
    "calculate_efficiency_score",
    "calculate_monthly_scores",
    "calculate_annual_scores",
    "classify_athlete",
    "get_experience_level",
    "should_save_to_database",
    "calculate_normalized_power",
    "calculate_normalized_power_with_error",
    "calculate_intensity_factor",
    "calculate_intensity_factor_with_error",
    "calculate_tss",
    "calculate_tss_with_error",
    "estimate_ftp_from_test",
    "estimate_ftp_from_test_with_error",
    "estimate_ftp_from_ride",
    "estimate_ftp_from_ride_with_error",
    "calculate_power_metrics",
    "calculate_power_metrics_with_error",
]
