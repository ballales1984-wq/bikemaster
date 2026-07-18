"""Validation layer for the physics kernel against measured power-meter data.

Confronta la potenza istantanea stimata da ``core.physics`` con la potenza
misurata dai power meter (``GPSPoint.power``) sulle ride reali, così da poter
tarare ``RiderBikeParams`` (CdA, Crr, massa) e quantificare il bias del modello.

La velocità istantanea è calcolata da distanza/tempo tra punti consecutivi
(``haversine`` + ``timestamp``), quindi è indipendente dall'unità di ``speed``
memorizzata sui punti GPS.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import GPSPoint, Ride
from .constants import RiderBikeParams
from .power import grade_between, instantaneous_power


@dataclass
class PowerValidationResult:
    """Statistiche di errore tra potenza stimata e misurata."""

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
    """Yield (measured_power, v_ms, grade) per segmento con power-meter valido.

    Per ogni coppia consecutiva di punti GPS con power misurato e timestamp
    validi, calcola velocita' istantanea (distanza haversine / dt) e pendenza
    tra i due punti. Salta segmenti con dt <= 0 o distanza <= 0.

    Args:
        points: Lista di GPSPoint ordinati per timestamp.

    Yields:
        Tupla (potenza_misurata_W, velocita_ms, grade) per ogni segmento
        con dati power-meter validi.
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
    """Valida la potenza stimata contro i power-meter di una ``Ride``.

    Ritorna ``None`` se la ride non ha abbastanza dati di potenza misurati.
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

    # R^2 = 1 - SS_res / SS_tot: frazione di varianza spiegata dal modello
    ss_res = sum(e * e for e in errors)                  # somma quadrati residui
    ss_tot = sum((m - mean_m) ** 2 for m in measured)    # somma quadrati totali
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
    """Valida una lista di ride, ritornando solo quelle con dati sufficienti."""
    results: list[PowerValidationResult] = []
    for ride in rides:
        res = validate_ride_power(ride, params, wind_ms)
        if res is not None:
            results.append(res)
    return results
