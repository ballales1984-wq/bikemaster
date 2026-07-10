"""BikeMaster 2.0 - Transformation Layer (il trasformatore universale).

Responsabilità del Transformer Engine:

1. **Unit Converter**  - normalizza tutte le unità verso lo standard interno.
2. **Geo Transformer** - coordinate geografiche -> coordinate metriche locali,
   distanze, pendenze, superfici.
3. **Time Transformer** - timestamp -> UTC -> ora locale -> intervalli.
4. **Data Quality**     - controlli di validità, stima della precisione per
   fonte/unità, rilevamento outlier.

Gli algoritmi NON devono mai convertire dati grezzi: ricevono sempre grandezze
già normalizzate tramite questo livello.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from typing import Iterable, Optional

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

# Precisione di default stimata per (fonte, unità) - valori tipici di mercato.
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
    """Punto geografico con proiezione metrica locale (equirettangolare)."""

    lat: float
    lon: float
    altitude: float = 0.0
    timestamp: Optional[datetime] = None
    x: float = 0.0
    y: float = 0.0
    speed: Optional[float] = None
    power: Optional[float] = None
    heart_rate: Optional[float] = None
    cadence: Optional[float] = None

    @property
    def meters(self) -> tuple[float, float]:
        return self.x, self.y


# ---------------------------------------------------------------------------
# 1. Unit Converter
# ---------------------------------------------------------------------------
class UnitConverter:
    def __init__(self, registry: UnitRegistry | None = None) -> None:
        self.registry = registry or default_registry

    def to_internal(self, quantity: Quantity) -> Quantity:
        """Normalizza una grandezza verso l'unità canonica interna."""
        return self.registry.to_canonical(quantity)

    def convert(self, quantity: Quantity, target_unit: str) -> Quantity:
        return self.registry.convert(quantity, target_unit)

    def estimate_precision(self, value: float, unit: str, source: str) -> float:
        return DEFAULT_QUALITY.get((source, unit), abs(value) * 0.02 + 0.5)


# ---------------------------------------------------------------------------
# 2. Geo Transformer
# ---------------------------------------------------------------------------
class GeoTransformer:
    def project(self, lat: float, lon: float, ref_lat: float) -> tuple[float, float]:
        """Proiezione equirettangolare locale (metri) rispetto a `ref_lat`."""
        x = math.radians(lon) * EARTH_RADIUS_M * math.cos(math.radians(ref_lat))
        y = math.radians(lat) * EARTH_RADIUS_M
        return x, y

    def to_metric_points(self, points: Iterable[GeoPoint]) -> list[GeoPoint]:
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
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        return 2 * EARTH_RADIUS_M * math.asin(
            math.sqrt(math.sin(dphi / 2) ** 2
                      + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        )

    def distance_2d_m(self, a: GeoPoint, b: GeoPoint) -> float:
        """Distanza orizzontale tra due punti proiettati (metrica locale)."""
        return math.hypot(b.x - a.x, b.y - a.y)

    def slope_percent(self, rise_m: float, run_m: float) -> float:
        """Pendenza in percentuale (tan * 100)."""
        if run_m <= 0:
            return 0.0
        return (rise_m / run_m) * 100.0

    def bearing_deg(self, a: GeoPoint, b: GeoPoint) -> float:
        return math.degrees(math.atan2(b.x - a.x, b.y - a.y)) % 360.0

    def track_metrics(self, points: list[GeoPoint]) -> dict:
        """Distanza, dislivello e pendenza media su una traccia proiettata."""
        if len(points) < 2:
            return {"distance_m": 0.0, "gain_m": 0.0, "loss_m": 0.0,
                    "avg_slope_percent": 0.0}
        pts = self.to_metric_points(points)
        dist = 0.0
        gain = 0.0
        loss = 0.0
        for a, b in zip(pts, pts[1:]):
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
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    @staticmethod
    def to_local(dt: datetime, tz: timezone) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(tz)

    @staticmethod
    def interval_seconds(a: datetime, b: datetime) -> float:
        return (TimeTransformer.to_utc(b) - TimeTransformer.to_utc(a)).total_seconds()

    @staticmethod
    def duration_from_points(points: list[GeoPoint]) -> float:
        ts = [p.timestamp for p in points if p.timestamp is not None]
        if len(ts) < 2:
            return 0.0
        return (TimeTransformer.to_utc(ts[-1]) - TimeTransformer.to_utc(ts[0])).total_seconds()


# ---------------------------------------------------------------------------
# 4. Data Quality
# ---------------------------------------------------------------------------
@dataclass
class RangeRule:
    unit: str
    min_value: float
    max_value: float


class DataQuality:
    # Range plausibili per unità (usati per rilevare valori errati).
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
        rng = self.RANGES.get(quantity.unit)
        if rng is None:
            return True
        return rng[0] <= quantity.value <= rng[1]

    def check(self, quantity: Quantity) -> list[str]:
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
        problems: list[str] = []
        ts = [q.timestamp for q in quantities if q.timestamp is not None]
        if len(ts) < 2:
            return problems
        if ts != sorted(ts):
            problems.append("timestamp non ordinate")
        gaps = [
            (TimeTransformer.interval_seconds(a, b), a, b)
            for a, b in zip(ts, ts[1:])
        ]
        if max_gap_seconds > 0:
            for gap, a, b in gaps:
                if gap > max_gap_seconds:
                    problems.append(
                        f"salto temporale {gap:.0f}s tra {a} e {b}"
                    )
        return problems

    def outlier_score(self, quantity: Quantity, median: float) -> float:
        """Scarto normalizzato rispetto alla mediana (0 = coerente)."""
        if quantity.precision <= 0:
            return 0.0
        return abs(quantity.value - median) / max(quantity.precision, 1e-9)


# ---------------------------------------------------------------------------
# Engine composto
# ---------------------------------------------------------------------------
class TransformerEngine:
    """Motore di trasformazione centralizzato: unità + geo + tempo + qualità."""

    def __init__(self, registry: UnitRegistry | None = None) -> None:
        self.units = UnitConverter(registry)
        self.geo = GeoTransformer()
        self.time = TimeTransformer()
        self.quality = DataQuality()

    def normalize(self, quantity: Quantity) -> Quantity:
        """Converte a unità canonica e completa la precisione se mancante."""
        qn = self.units.to_internal(quantity)
        if qn.precision == 0.0:
            precision = self.units.estimate_precision(qn.value, qn.unit, qn.source)
            qn = Quantity(qn.value, qn.unit, precision, qn.source, qn.timestamp)
        return qn

    def power_to_weight(self, power: Quantity, weight: Quantity) -> Quantity:
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
