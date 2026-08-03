"""BikeMaster 2.0 - Transformation Layer (the universal transformer).

Transformer Engine responsibilities:

1. **Unit Converter**  - normalizes all units to the internal standard.
2. **Geo Transformer** - geographic coordinates -> local metric coordinates,
   distances, slopes, surfaces.
3. **Time Transformer** - timestamp -> UTC -> local time -> intervals.
4. **Data Quality**     - validity checks, precision estimation per
   source/unit, outlier detection.

Algorithms MUST NEVER convert raw data: they always receive quantities
already normalized through this layer.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timezone

from .units import Quantity, UnitRegistry, default_registry

__all__ = [
    "GeoPoint",
    "UnitConverter",
    "GeoTransformer",
    "TimeTransformer",
    "DataQuality",
    "TransformerEngine",
    "DEFAULT_QUALITY",
]

EARTH_RADIUS_M = 6_371_000.0

# Default estimated precision for (source, unit) - typical market values.
DEFAULT_QUALITY: dict[tuple[str, str], float] = {
    ("manual", "kg"): 0.1,
    ("scale", "kg"): 0.1,
    ("manual", "m"): 1.0,
    ("gps", "m"): 5.0,           # posizione orizzontale ±5 m
    ("gps/dem", "m"): 10.0,      # quota da GPS/DEM ±10 m
    ("baro", "m"): 1.0,
    ("hr_band", "bpm"): 1.0,
    ("hr_sensor", "bpm"): 1.0,
    ("power_meter", "W"): 2.0,
    ("estimate", "W"): 15.0,
    ("manual", "km/h"): 0.5,
    ("gps", "km/h"): 0.5,
    ("manual", "%"): 0.5,
    ("dem", "%"): 2.0,
    ("manual", "mmHg"): 1.0,
    ("manual", "W/kg"): 0.05,
    ("manual", "Nm"): 0.5,
    ("manual", "g/L"): 0.01,
}


@dataclass(frozen=True)
class GeoPoint:
    """Geographic point with local metric projection (equirectangular)."""

    lat: float
    lon: float
    altitude: float = 0.0
    timestamp: datetime | None = None
    x: float = 0.0
    y: float = 0.0
    speed: float | None = None
    power: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None

    @property
    def meters(self) -> tuple[float, float]:
        """Local metric coordinates (x, y) in meters."""
        return self.x, self.y


# ---------------------------------------------------------------------------
# 1. Unit Converter
# ---------------------------------------------------------------------------
class UnitConverter:
    """Converts measurement units to the internal canonical standard."""

    def __init__(self, registry: UnitRegistry | None = None) -> None:
        """Registers the unit registry or uses the default one."""
        self.registry = registry or default_registry

    def to_internal(self, quantity: Quantity) -> Quantity:
        """Normalizes a quantity toward the internal canonical unit."""
        return self.registry.to_canonical(quantity)

    def convert(self, quantity: Quantity, target_unit: str) -> Quantity:
        """Converts a quantity to a specific target unit."""
        return self.registry.convert(quantity, target_unit)

    def estimate_precision(self, value: float, unit: str, source: str) -> float:
        """Estimates typical precision for (source, unit) or uses a default value."""
        return DEFAULT_QUALITY.get((source, unit), abs(value) * 0.02 + 0.5)


# ---------------------------------------------------------------------------
# 2. Geo Transformer
# ---------------------------------------------------------------------------
class GeoTransformer:
    """Geographic projections, distances, slopes, and track metrics."""

    def project(self, lat: float, lon: float, ref_lat: float) -> tuple[float, float]:
        """Local equirectangular projection (meters) relative to `ref_lat`."""
        x = math.radians(lon) * EARTH_RADIUS_M * math.cos(math.radians(ref_lat))
        y = math.radians(lat) * EARTH_RADIUS_M
        return x, y

    def to_metric_points(self, points: Iterable[GeoPoint]) -> list[GeoPoint]:
        """Projects GPS points to local metric coordinates (equirectangular)."""
        pts = list(points)
        if not pts:
            return []
        ref_lat = sum(p.lat for p in pts) / len(pts)
        out = []
        for p in pts:
            x, y = self.project(p.lat, p.lon, ref_lat)
            out.append(GeoPoint(lat=p.lat, lon=p.lon, altitude=p.altitude,
                                timestamp=p.timestamp, x=x, y=y))
        return out

    @staticmethod
    def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distanza sferica (metri) tra due coordinate tramite formula di Haversine."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        return 2 * EARTH_RADIUS_M * math.asin(
            math.sqrt(math.sin(dphi / 2) ** 2
                      + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        )

    def distance_2d_m(self, a: GeoPoint, b: GeoPoint) -> float:
        """Horizontal distance between two projected points (local metric)."""
        return math.hypot(b.x - a.x, b.y - a.y)

    def slope_percent(self, rise_m: float, run_m: float) -> float:
        """Slope percentage (tan * 100)."""
        if run_m <= 0:
            return 0.0
        return (rise_m / run_m) * 100.0

    def bearing_deg(self, a: GeoPoint, b: GeoPoint) -> float:
        """Direction (degrees) from point A to point B in local projection."""
        return math.degrees(math.atan2(b.x - a.x, b.y - a.y)) % 360.0

    def track_metrics(self, points: list[GeoPoint]) -> dict:
        """Distance, elevation gain/loss and average slope on a projected track."""
        if len(points) < 2:
            return {"distance_m": 0.0, "gain_m": 0.0, "loss_m": 0.0,
                    "avg_slope_percent": 0.0}
        pts = self.to_metric_points(points)
        dist = 0.0
        gain = 0.0
        loss = 0.0
        for a, b in zip(pts, pts[1:], strict=False):
            dist += self.distance_2d_m(a, b)
            dz = b.altitude - a.altitude
            if dz > 0:
                gain += dz
            else:
                loss += -dz
        run = max(dist, 1e-6)
        net = pts[-1].altitude - pts[0].altitude
        return {
            "distance_m": dist,
            "gain_m": gain,
            "loss_m": loss,
            "avg_slope_percent": self.slope_percent(net, run),
        }


# ---------------------------------------------------------------------------
# 3. Time Transformer
# ---------------------------------------------------------------------------
class TimeTransformer:
    """Time conversions and intervals (UTC, local, durations)."""

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Converts a timestamp to UTC (assumes naive as UTC)."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    @staticmethod
    def to_local(dt: datetime, tz: timezone) -> datetime:
        """Converts a timestamp to a specified local timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(tz)

    @staticmethod
    def interval_seconds(a: datetime, b: datetime) -> float:
        """Seconds interval between two timestamps (in UTC)."""
        return (TimeTransformer.to_utc(b) - TimeTransformer.to_utc(a)).total_seconds()

    @staticmethod
    def duration_from_points(points: list[GeoPoint]) -> float:
        """Duration in seconds between first and last point with valid timestamp."""
        ts = [p.timestamp for p in points if p.timestamp is not None]
        if len(ts) < 2:
            return 0.0
        return (TimeTransformer.to_utc(ts[-1]) - TimeTransformer.to_utc(ts[0])).total_seconds()


# ---------------------------------------------------------------------------
# 4. Data Quality
# ---------------------------------------------------------------------------
@dataclass
class RangeRule:
    """Range rule for quantity validation."""

    unit: str
    min_value: float
    max_value: float


class DataQuality:
    """Validity checks, precision estimation and outlier detection for quantities."""

    RANGES: dict[str, tuple[float, float]] = {
        "kg": (20.0, 250.0),
        "bpm": (20.0, 230.0),
        "W": (0.0, 1500.0),
        "m/s": (0.0, 40.0),
        "%": (-40.0, 40.0),
        "°C": (-30.0, 50.0),
        "W/kg": (0.0, 30.0),
        "Nm": (0.0, 100.0),
        "mmHg": (300.0, 800.0),
        "g/L": (0.5, 2.0),
    }

    def in_range(self, quantity: Quantity) -> bool:
        """Checks if the value is in the plausible range for its unit."""
        rng = self.RANGES.get(quantity.unit)
        if rng is None:
            return True
        return rng[0] <= quantity.value <= rng[1]

    def check(self, quantity: Quantity) -> list[str]:
        """Returns a list of quality problems for the quantity."""
        problems: list[str] = []
        if not self.in_range(quantity):
            lo, hi = self.RANGES[quantity.unit]
            problems.append(
                f"{quantity.value} {quantity.unit} fuori range plausibile [{lo}, {hi}]"
            )
        if quantity.precision < 0:
            problems.append("precisione negativa")
        return problems

    def check_temporal(self, quantities: list[Quantity], max_gap_seconds: float = 0.0) -> list[str]:
        """Checks timestamp ordering and excessive temporal gaps."""
        problems: list[str] = []
        ts = [q.timestamp for q in quantities if q.timestamp is not None]
        if len(ts) < 2:
            return problems
        if ts != sorted(ts):
            problems.append("timestamp non ordinate")
        gaps = [
            (TimeTransformer.interval_seconds(a, b), a, b)
            for a, b in zip(ts, ts[1:], strict=False)
        ]
        if max_gap_seconds > 0:
            for gap, a, b in gaps:
                if gap > max_gap_seconds:
                    problems.append(
                        f"salto temporale {gap:.0f}s tra {a} e {b}"
                    )
        return problems

    def outlier_score(self, quantity: Quantity, median: float) -> float:
        """Normalized deviation from median (0 = consistent)."""
        if quantity.precision <= 0:
            return 0.0
        return abs(quantity.value - median) / max(quantity.precision, 1e-9)


# ---------------------------------------------------------------------------
# Engine composto
# ---------------------------------------------------------------------------
class TransformerEngine:
    """Centralized transformation engine: units + geo + time + quality."""

    def __init__(self, registry: UnitRegistry | None = None) -> None:
        """Initializes the engine with converter, geo, time and quality checks."""
        self.units = UnitConverter(registry)
        self.geo = GeoTransformer()
        self.time = TimeTransformer()
        self.quality = DataQuality()

    def normalize(self, quantity: Quantity) -> Quantity:
        """Converts to canonical unit and completes precision if missing."""
        qn = self.units.to_internal(quantity)
        if qn.precision == 0.0:
            precision = self.units.estimate_precision(qn.value, qn.unit, qn.source)
            qn = Quantity(qn.value, qn.unit, precision, qn.source, qn.timestamp)
        return qn

    def power_to_weight(self, power: Quantity, weight: Quantity) -> Quantity:
        """Calculates the power-to-weight ratio (W/kg) with error propagation."""
        pw = self.units.to_internal(power)
        wt = self.units.to_internal(weight)
        if pw.unit != "W" or wt.unit != "kg":
            raise ValueError("power_to_weight richiede W e kg")
        value = pw.value / wt.value
        rel_err = math.sqrt((pw.precision / pw.value) ** 2 + (wt.precision / wt.value) ** 2)
        precision = abs(value) * rel_err
        return Quantity(value=value, unit="W/kg", precision=precision,
                        source=f"{pw.source}/{wt.source}",
                        timestamp=pw.timestamp or wt.timestamp)

    def air_density(self, temperature: Quantity, pressure: Quantity) -> Quantity:
        """Calcola la densita' dell'aria (kg/m^3) da temperatura e pressione."""
        temp = self.units.to_internal(temperature)
        pres = self.units.to_internal(pressure)
        if temp.unit != "°C" or pres.unit != "Pa":
            raise ValueError("air_density richiede °C e Pa")
        t_k = temp.value + 273.15
        rho = pres.value / (287.05 * t_k)
        rel_err = math.sqrt(
            (pres.precision / pres.value) ** 2 + (temp.precision / t_k) ** 2
        )
        precision = abs(rho) * rel_err
        return Quantity(value=rho, unit="kg/m^3", precision=precision,
                        source=f"{temp.source}/{pres.source}",
                        timestamp=temp.timestamp or pres.timestamp)
