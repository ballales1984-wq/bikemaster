"""Validation layer for the physics kernel against measured power-meter data.

Compares instantaneous power estimated by ``core.physics`` with power
measured by power meters (``GPSPoint.power``) on real rides, so we can
calibrate ``RiderBikeParams`` (CdA, Crr, mass) and quantify model bias.

Instantaneous speed is calculated from distance/time between consecutive points
(``haversine`` + ``timestamp``), so it is independent of the ``speed`` unit
stored on GPS points.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import GPSPoint, Ride
from .constants import RiderBikeParams
from .power import grade_between, instantaneous_power


@dataclass
class PowerValidationResult:
    """Error statistics between estimated and measured power."""

    n_points: int
    mae_w: float
    rmse_w: float
    bias_w: float
    mean_measured_w: float
    mean_estimated_w: float
    r2: float

    def to_dict(self) -> dict:
        return {
            "n_points": self.n_points,
            "mae_w": round(self.mae_w, 3),
            "rmse_w": round(self.rmse_w, 3),
            "bias_w": round(self.bias_w, 3),
            "mean_measured_w": round(self.mean_measured_w, 3),
            "mean_estimated_w": round(self.mean_estimated_w, 3),
            "r2": round(self.r2, 4),
        }


def _segment_pairs(points: list[GPSPoint]):
    """Yield (measured_power, v_ms, grade) per segment with valid power-meter.

    For each consecutive pair of GPS points with measured power and valid
    timestamps, calculates instantaneous speed (haversine distance / dt) and slope
    between the two points. Skips segments with dt <= 0 or distance <= 0.

    Args:
        points: List of GPSPoint ordered by timestamp.

    Yields:
        Tuple (measured_power_W, speed_ms, grade) for each segment
        with valid power-meter data.
    """
    from ..models import haversine_distance_m

    for prev, cur in zip(points, points[1:]):
        if cur.power is None:
            continue
        if prev.timestamp is None or cur.timestamp is None:
            continue
        dt = (cur.timestamp - prev.timestamp).total_seconds()
        if dt <= 0:
            continue
        ds = haversine_distance_m(prev.lat, prev.lon, cur.lat, cur.lon)
        if ds <= 0:
            continue
        v_ms = ds / dt
        grade = grade_between(prev, cur)
        yield cur.power, v_ms, grade


def validate_ride_power(
    ride: Ride,
    params: RiderBikeParams | None = None,
    wind_ms: float = 0.0,
    min_points: int = 5,
) -> PowerValidationResult | None:
    """Validates estimated power against power-meters of a ``Ride``.

    Returns ``None`` if the ride does not have enough measured power data.
    """
    if not ride.gps_points or len(ride.gps_points) < 2:
        return None

    pairs = list(_segment_pairs(ride.gps_points))
    if len(pairs) < min_points:
        return None

    measured: list[float] = []
    estimated: list[float] = []
    for m_power, v_ms, grade in pairs:
        measured.append(float(m_power))
        estimated.append(instantaneous_power(v_ms, grade, params, wind_ms))

    n = len(measured)
    mean_m = sum(measured) / n
    mean_e = sum(estimated) / n
    errors = [e - m for e, m in zip(estimated, measured)]
    mae = sum(abs(e) for e in errors) / n
    rmse = (sum(e * e for e in errors) / n) ** 0.5
    bias = mean_e - mean_m

    # R^2 = 1 - SS_res / SS_tot: fraction of variance explained by the model
    ss_res = sum(e * e for e in errors)                  # residual sum of squares
    ss_tot = sum((m - mean_m) ** 2 for m in measured)    # total sum of squares
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return PowerValidationResult(
        n_points=n,
        mae_w=mae,
        rmse_w=rmse,
        bias_w=bias,
        mean_measured_w=mean_m,
        mean_estimated_w=mean_e,
        r2=r2,
    )


def validate_rides(
    rides: list[Ride],
    params: RiderBikeParams | None = None,
    wind_ms: float = 0.0,
) -> list[PowerValidationResult]:
    """Validates a list of rides, returning only those with sufficient data."""
    results: list[PowerValidationResult] = []
    for ride in rides:
        res = validate_ride_power(ride, params, wind_ms)
        if res is not None:
            results.append(res)
    return results

