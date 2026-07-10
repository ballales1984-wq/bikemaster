"""BikeMaster 2.0 - Core Model (gli oggetti principali del dominio).

Ogni oggetto è costruito a partire da dati grezzi tramite il
:class:`~bike_analyzer.bm2.transformer.TransformerEngine`, così che gli
algoritmi trovino sempre grandezze normalizzate (unità canoniche interne).

Oggetti principali:
    Athlete     - il corpo umano e la sua capacità
    Bike        - la bici e la sua efficienza
    Activity    - un'uscita / giro con la sua traccia
    WorldObject - il territorio (terreno, strada, montagna)
    AnalysisContext - il contesto completo passato agli algoritmi
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .transformer import GeoPoint, TransformerEngine
from .units import Quantity, q

__all__ = [
    "Athlete", "Bike", "Activity", "WorldObject", "AnalysisContext",
]


def _quantity_to_dict(quantity: Quantity) -> dict:
    return {
        "value": quantity.value,
        "unit": quantity.unit,
        "precision": quantity.precision,
        "source": quantity.source,
        "timestamp": quantity.timestamp.isoformat() if quantity.timestamp else None,
    }


def _quantity_from_dict(raw: dict, t: TransformerEngine) -> Quantity:
    ts = datetime.fromisoformat(raw["timestamp"]) if raw.get("timestamp") else None
    quantity = Quantity(
        value=float(raw["value"]),
        unit=raw["unit"],
        precision=float(raw.get("precision", 0.0)),
        source=raw.get("source", "unknown"),
        timestamp=ts,
    )
    if quantity.precision == 0.0:
        precision = t.units.estimate_precision(quantity.value, quantity.unit, quantity.source)
        quantity = Quantity(quantity.value, quantity.unit, precision, quantity.source, quantity.timestamp)
    if t.units.registry.dimension_of(quantity.unit) is not None:
        return t.units.registry.to_canonical(quantity)
    return quantity


@dataclass
class Athlete:
    weight_kg: Quantity
    age: int = 30
    height_m: Optional[Quantity] = None
    ftp_w: Optional[Quantity] = None
    max_hr_bpm: Optional[Quantity] = None
    resting_hr_bpm: Optional[Quantity] = None
    experience_level: str = "Beginner"
    weekly_hours: Optional[Quantity] = None
    name: str = ""
    ctl_stress_score: Optional[Quantity] = None
    atl_stress_score: Optional[Quantity] = None
    tsb_stress_score: Optional[Quantity] = None

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> "Athlete":
        if raw.get("weight") is None:
            raise ValueError("campo obbligatorio 'weight' mancante per Athlete")
        weight = t.normalize(q(raw.get("weight"), raw.get("weight_unit", "kg"),
                               source=raw.get("source", "manual")))
        height = None
        if raw.get("height") is not None:
            height = t.normalize(q(raw["height"], raw.get("height_unit", "m"),
                                   source=raw.get("source", "manual")))
        ftp = None
        if raw.get("ftp") is not None:
            ftp = t.normalize(q(raw["ftp"], "W", source=raw.get("ftp_source", "estimate")))
        max_hr = None
        if raw.get("max_hr") is not None:
            max_hr = t.normalize(q(raw["max_hr"], "bpm", source="manual"))
        rhr = None
        if raw.get("resting_hr") is not None:
            rhr = t.normalize(q(raw["resting_hr"], "bpm", source="manual"))
        wh = None
        if raw.get("weekly_hours") is not None:
            wh = t.normalize(q(raw["weekly_hours"], "h", source="manual"))
        ctl = None
        if raw.get("ctl") is not None:
            ctl = q(raw["ctl"], raw.get("ctl_unit", "score"), source=raw.get("source", "manual"))
        atl = None
        if raw.get("atl") is not None:
            atl = q(raw["atl"], raw.get("atl_unit", "score"), source=raw.get("source", "manual"))
        tsb = None
        if raw.get("tsb") is not None:
            tsb = q(raw["tsb"], raw.get("tsb_unit", "score"), source=raw.get("source", "manual"))
        return cls(
            weight_kg=weight,
            age=int(raw.get("age", 30)),
            height_m=height,
            ftp_w=ftp,
            max_hr_bpm=max_hr,
            resting_hr_bpm=rhr,
            experience_level=raw.get("experience_level", "Beginner"),
            weekly_hours=wh,
            name=raw.get("name", ""),
            ctl_stress_score=ctl,
            atl_stress_score=atl,
            tsb_stress_score=tsb,
        )

    def power_to_weight(self) -> Optional[float]:
        if self.ftp_w is None:
            return None
        return self.ftp_w.value / self.weight_kg.value

    def to_dict(self) -> dict:
        return {
            "weight_kg": _quantity_to_dict(self.weight_kg),
            "age": self.age,
            "height_m": _quantity_to_dict(self.height_m) if self.height_m else None,
            "ftp_w": _quantity_to_dict(self.ftp_w) if self.ftp_w else None,
            "max_hr_bpm": _quantity_to_dict(self.max_hr_bpm) if self.max_hr_bpm else None,
            "resting_hr_bpm": _quantity_to_dict(self.resting_hr_bpm) if self.resting_hr_bpm else None,
            "experience_level": self.experience_level,
            "weekly_hours": _quantity_to_dict(self.weekly_hours) if self.weekly_hours else None,
            "name": self.name,
            "ctl_stress_score": _quantity_to_dict(self.ctl_stress_score) if self.ctl_stress_score else None,
            "atl_stress_score": _quantity_to_dict(self.atl_stress_score) if self.atl_stress_score else None,
            "tsb_stress_score": _quantity_to_dict(self.tsb_stress_score) if self.tsb_stress_score else None,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> "Athlete":
        return cls(
            weight_kg=_quantity_from_dict(raw["weight_kg"], t),
            age=int(raw.get("age", 30)),
            height_m=_quantity_from_dict(raw["height_m"], t) if raw.get("height_m") else None,
            ftp_w=_quantity_from_dict(raw["ftp_w"], t) if raw.get("ftp_w") else None,
            max_hr_bpm=_quantity_from_dict(raw["max_hr_bpm"], t) if raw.get("max_hr_bpm") else None,
            resting_hr_bpm=_quantity_from_dict(raw["resting_hr_bpm"], t) if raw.get("resting_hr_bpm") else None,
            experience_level=raw.get("experience_level", "Beginner"),
            weekly_hours=_quantity_from_dict(raw["weekly_hours"], t) if raw.get("weekly_hours") else None,
            name=raw.get("name", ""),
            ctl_stress_score=_quantity_from_dict(raw["ctl_stress_score"], t) if raw.get("ctl_stress_score") else None,
            atl_stress_score=_quantity_from_dict(raw["atl_stress_score"], t) if raw.get("atl_stress_score") else None,
            tsb_stress_score=_quantity_from_dict(raw["tsb_stress_score"], t) if raw.get("tsb_stress_score") else None,
        )


@dataclass
class Bike:
    weight_kg: Quantity
    crr: float = 0.005
    cda: float = 0.40
    drivetrain_efficiency: float = 0.97
    name: str = ""
    category: str = "road"
    gear_ratio: Optional[float] = None

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> "Bike":
        if raw.get("weight") is None:
            raise ValueError("campo obbligatorio 'weight' mancante per Bike")
        weight = t.normalize(q(raw.get("weight"), raw.get("weight_unit", "kg"),
                               source=raw.get("source", "manual")))
        category = raw.get("category", "road")
        if category not in {"road", "gravel", "mtb", "other"}:
            raise ValueError(f"categoria bici non valida: {category!r}")
        gr = None
        if raw.get("gear_ratio") is not None:
            gr = float(raw["gear_ratio"])
        return cls(
            weight_kg=weight,
            crr=float(raw.get("crr", 0.005)),
            cda=float(raw.get("cda", 0.40)),
            drivetrain_efficiency=float(raw.get("drivetrain_efficiency", 0.97)),
            name=raw.get("name", ""),
            category=category,
            gear_ratio=gr,
        )

    def to_dict(self) -> dict:
        return {
            "weight_kg": _quantity_to_dict(self.weight_kg),
            "crr": self.crr,
            "cda": self.cda,
            "drivetrain_efficiency": self.drivetrain_efficiency,
            "name": self.name,
            "category": self.category,
            "gear_ratio": self.gear_ratio,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> "Bike":
        return cls(
            weight_kg=_quantity_from_dict(raw["weight_kg"], t),
            crr=float(raw.get("crr", 0.005)),
            cda=float(raw.get("cda", 0.40)),
            drivetrain_efficiency=float(raw.get("drivetrain_efficiency", 0.97)),
            name=raw.get("name", ""),
            category=raw.get("category", "road"),
            gear_ratio=float(raw["gear_ratio"]) if raw.get("gear_ratio") is not None else None,
        )


@dataclass
class Activity:
    """Un giro: traccia GPS + sensori. Le metriche sono calcolate a richiesta."""

    points: list[GeoPoint] = field(default_factory=list)
    title: str = ""
    sport: str = "cycling"
    laps: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def metrics(self, t: TransformerEngine) -> dict:
        """Metriche derivate normalizzate dalla traccia (tramite Geo/Time)."""
        pts = t.geo.to_metric_points(self.points)
        geo = t.geo.track_metrics(pts)
        duration_s = t.time.duration_from_points(self.points)
        dist_m = geo["distance_m"]
        speed_ms = dist_m / duration_s if duration_s > 0 else 0.0
        return {
            "distance_m": dist_m,
            "duration_s": duration_s,
            "gain_m": geo["gain_m"],
            "loss_m": geo["loss_m"],
            "avg_slope_percent": geo["avg_slope_percent"],
            "avg_speed_ms": speed_ms,
        }

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> "Activity":
        gps = raw.get("gps_points") or raw.get("points")
        if not gps:
            raise ValueError("campo obbligatorio 'gps_points'/'points' mancante per Activity")
        points = []
        for p in gps:
            ts = None
            if p.get("timestamp"):
                ts = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
            points.append(GeoPoint(
                lat=float(p["lat"]),
                lon=float(p["lon"]),
                altitude=float(p.get("altitude", 0.0)),
                timestamp=ts,
                x=float(p.get("x", 0.0)),
                y=float(p.get("y", 0.0)),
                speed=float(p["speed"]) if p.get("speed") is not None else None,
                power=float(p["power"]) if p.get("power") is not None else None,
                heart_rate=float(p["heart_rate"]) if p.get("heart_rate") is not None else None,
                cadence=float(p["cadence"]) if p.get("cadence") is not None else None,
            ))
        return cls(
            points=points,
            title=raw.get("title", ""),
            sport=raw.get("sport", "cycling"),
            laps=raw.get("laps", []),
            segments=raw.get("segments", []),
            summary=raw.get("summary", {}),
        )

    def to_dict(self) -> dict:
        return {
            "points": [
                {
                    "lat": p.lat,
                    "lon": p.lon,
                    "altitude": p.altitude,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    "x": p.x,
                    "y": p.y,
                    "speed": p.speed,
                    "power": p.power,
                    "heart_rate": p.heart_rate,
                    "cadence": p.cadence,
                }
                for p in self.points
            ],
            "title": self.title,
            "sport": self.sport,
            "laps": self.laps,
            "segments": self.segments,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> "Activity":
        points = []
        for p in raw.get("points", []):
            ts = None
            if p.get("timestamp"):
                ts = datetime.fromisoformat(p["timestamp"])
            points.append(GeoPoint(
                lat=float(p["lat"]),
                lon=float(p["lon"]),
                altitude=float(p.get("altitude", 0.0)),
                timestamp=ts,
                x=float(p.get("x", 0.0)),
                y=float(p.get("y", 0.0)),
                speed=float(p["speed"]) if p.get("speed") is not None else None,
                power=float(p["power"]) if p.get("power") is not None else None,
                heart_rate=float(p["heart_rate"]) if p.get("heart_rate") is not None else None,
                cadence=float(p["cadence"]) if p.get("cadence") is not None else None,
            ))
        return cls(
            points=points,
            title=raw.get("title", ""),
            sport=raw.get("sport", "cycling"),
            laps=raw.get("laps", []),
            segments=raw.get("segments", []),
            summary=raw.get("summary", {}),
        )


@dataclass
class WorldObject:
    """Il territorio attraversato dall'attività."""

    surface: str = "asphalt"
    roughness_index: Quantity = field(default_factory=lambda: q(0.0, "", source="manual"))
    avg_slope_percent: Optional[Quantity] = None
    wind_speed_ms: Optional[Quantity] = None
    temperature_c: Optional[Quantity] = None

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> "WorldObject":
        slope = None
        if raw.get("avg_slope") is not None:
            slope = t.normalize(q(raw["avg_slope"], raw.get("avg_slope_unit", "%"),
                                  source=raw.get("source", "dem")))
        wind = None
        if raw.get("wind_speed") is not None:
            wind = t.normalize(q(raw["wind_speed"], "m/s", source="manual"))
        temp = None
        if raw.get("temperature") is not None:
            temp = t.normalize(q(raw["temperature"], "°C", source="manual"))
        rough = q(float(raw.get("roughness_index", 0.0)), "", source="manual")
        return cls(
            surface=raw.get("surface", "asphalt"),
            roughness_index=rough,
            avg_slope_percent=slope,
            wind_speed_ms=wind,
            temperature_c=temp,
        )

    def to_dict(self) -> dict:
        return {
            "surface": self.surface,
            "roughness_index": _quantity_to_dict(self.roughness_index),
            "avg_slope_percent": _quantity_to_dict(self.avg_slope_percent) if self.avg_slope_percent else None,
            "wind_speed_ms": _quantity_to_dict(self.wind_speed_ms) if self.wind_speed_ms else None,
            "temperature_c": _quantity_to_dict(self.temperature_c) if self.temperature_c else None,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> "WorldObject":
        return cls(
            surface=raw.get("surface", "asphalt"),
            roughness_index=_quantity_from_dict(raw["roughness_index"], t),
            avg_slope_percent=_quantity_from_dict(raw["avg_slope_percent"], t) if raw.get("avg_slope_percent") else None,
            wind_speed_ms=_quantity_from_dict(raw["wind_speed_ms"], t) if raw.get("wind_speed_ms") else None,
            temperature_c=_quantity_from_dict(raw["temperature_c"], t) if raw.get("temperature_c") else None,
        )


@dataclass
class AnalysisContext:
    """Contesto completo passato agli algoritmi del Model Engine."""

    athlete: Athlete
    activity: Activity
    bike: Bike
    world: WorldObject
    transformer: TransformerEngine

    @property
    def total_mass_kg(self) -> float:
        return self.athlete.weight_kg.value + self.bike.weight_kg.value

    def to_dict(self) -> dict:
        return {
            "athlete": self.athlete.to_dict(),
            "activity": self.activity.to_dict(),
            "bike": self.bike.to_dict(),
            "world": self.world.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> "AnalysisContext":
        return cls(
            athlete=Athlete.from_dict(raw["athlete"], t),
            activity=Activity.from_dict(raw["activity"], t),
            bike=Bike.from_dict(raw["bike"], t),
            world=WorldObject.from_dict(raw["world"], t),
            transformer=t,
        )
