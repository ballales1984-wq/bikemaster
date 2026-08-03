"""BikeMaster 2.0 - Core Model (main domain objects).

Each object is built from raw data via the
:class:`~bike_analyzer.bm2.transformer.TransformerEngine`, so algorithms
always find normalized quantities (internal canonical units).

Main objects:
    Athlete     - the human body and its athletic capacity
    Bike        - the bike and its efficiency
    Activity    - a ride / trip with its track
    WorldObject - the territory (terrain, road, mountain)
    AnalysisContext - the complete context passed to algorithms
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .transformer import GeoPoint, TransformerEngine
from .units import Quantity, q

__all__ = [
    "Athlete",
    "Bike",
    "Activity",
    "WorldObject",
    "AnalysisContext",
    "MetabolicProfile",
    "MetabolicDailySummary",
]


def _quantity_to_dict(quantity: Quantity) -> dict:
    """Serializes a Quantity to JSON-compatible dictionary."""
    return {
        "value": quantity.value,
        "unit": quantity.unit,
        "precision": quantity.precision,
        "source": quantity.source,
        "timestamp": quantity.timestamp.isoformat() if quantity.timestamp else None,
    }


def _quantity_from_dict(raw: dict, t: TransformerEngine) -> Quantity:
    """Reconstructs a Quantity from dictionary, completing precision if missing."""
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
    """The human body and its athletic capacity."""

    weight_kg: Quantity
    age: int = 30
    height_m: Quantity | None = None
    ftp_w: Quantity | None = None
    max_hr_bpm: Quantity | None = None
    resting_hr_bpm: Quantity | None = None
    experience_level: str = "Beginner"
    weekly_hours: Quantity | None = None
    name: str = ""
    ctl_stress_score: Quantity | None = None
    atl_stress_score: Quantity | None = None
    tsb_stress_score: Quantity | None = None
    fat_percentage: float | None = None
    sex: str = "male"
    bmr_formula: str = "mifflin"
    activity_level: str = "moderate"

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> Athlete:
        """Builds Athlete from raw data, normalizing units."""
        if raw.get("weight") is None:
            raise ValueError("required field 'weight' missing for Athlete")
        weight = t.normalize(q(raw.get("weight"), raw.get("weight_unit", "kg"), source=raw.get("source", "manual")))
        height = None
        if raw.get("height") is not None:
            height = t.normalize(q(raw["height"], raw.get("height_unit", "m"), source=raw.get("source", "manual")))
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
            fat_percentage=raw.get("fat_percentage"),
            sex=raw.get("sex", "male"),
            bmr_formula=raw.get("bmr_formula", "mifflin"),
            activity_level=raw.get("activity_level", "moderate"),
        )

    def power_to_weight(self) -> float | None:
        """Power-to-weight ratio (W/kg) from FTP, None if FTP not defined."""
        if self.ftp_w is None:
            return None
        return self.ftp_w.value / self.weight_kg.value

    def to_dict(self) -> dict:
        """Serializes the athlete to JSON-compatible dictionary."""
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
            "fat_percentage": self.fat_percentage,
            "sex": self.sex,
            "bmr_formula": self.bmr_formula,
            "activity_level": self.activity_level,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> Athlete:
        """Reconstructs Athlete from serialized dictionary."""
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
            fat_percentage=raw.get("fat_percentage"),
            sex=raw.get("sex", "male"),
            bmr_formula=raw.get("bmr_formula", "mifflin"),
            activity_level=raw.get("activity_level", "moderate"),
        )


@dataclass
class MetabolicProfile:
    """Computed metabolic profile for an athlete (BMR, TDEE, NEAT)."""

    bmr_kcal: float = 0.0
    tdee_kcal: float = 0.0
    neat_kcal: float = 0.0
    eat_kcal: float = 0.0
    climb_bonus_kcal: float = 0.0
    bmr_formula: str = "mifflin"
    activity_level: str = "moderate"
    sex: str = "male"
    fat_percentage: float | None = None
    age: int = 30
    weight_kg: float = 70.0
    height_cm: float | None = None
    reference_bmr_kcal: float = 0.0
    reference_tdee_kcal: float = 0.0
    sensor_bmr_conf: float = 1.0
    sensor_tdee_conf: float = 1.0
    activity_multiplier_w: float = 1.0
    neat_w: float = 1.0
    climb_bonus_w: float = 1.0
    n_calibrations: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "bmr_kcal": round(self.bmr_kcal, 1),
            "tdee_kcal": round(self.tdee_kcal, 1),
            "neat_kcal": round(self.neat_kcal, 1),
            "eat_kcal": round(self.eat_kcal, 1),
            "climb_bonus_kcal": round(self.climb_bonus_kcal, 1),
            "bmr_formula": self.bmr_formula,
            "activity_level": self.activity_level,
            "sex": self.sex,
            "fat_percentage": self.fat_percentage,
            "age": self.age,
            "weight_kg": round(self.weight_kg, 1),
            "height_cm": round(self.height_cm, 1) if self.height_cm else None,
            "reference_bmr_kcal": round(self.reference_bmr_kcal, 1),
            "reference_tdee_kcal": round(self.reference_tdee_kcal, 1),
            "sensor_bmr_conf": round(self.sensor_bmr_conf, 4),
            "sensor_tdee_conf": round(self.sensor_tdee_conf, 4),
            "activity_multiplier_w": round(self.activity_multiplier_w, 4),
            "neat_w": round(self.neat_w, 4),
            "climb_bonus_w": round(self.climb_bonus_w, 4),
            "n_calibrations": self.n_calibrations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> MetabolicProfile:
        return cls(
            bmr_kcal=float(raw.get("bmr_kcal", 0.0) or 0.0),
            tdee_kcal=float(raw.get("tdee_kcal", 0.0) or 0.0),
            neat_kcal=float(raw.get("neat_kcal", 0.0) or 0.0),
            eat_kcal=float(raw.get("eat_kcal", 0.0) or 0.0),
            climb_bonus_kcal=float(raw.get("climb_bonus_kcal", 0.0) or 0.0),
            bmr_formula=raw.get("bmr_formula", "mifflin"),
            activity_level=raw.get("activity_level", "moderate"),
            sex=raw.get("sex", "male"),
            fat_percentage=raw.get("fat_percentage"),
            age=int(raw.get("age", 30)),
            weight_kg=float(raw.get("weight_kg", 70.0) or 70.0),
            height_cm=raw.get("height_cm"),
            reference_bmr_kcal=float(raw.get("reference_bmr_kcal", 0.0) or 0.0),
            reference_tdee_kcal=float(raw.get("reference_tdee_kcal", 0.0) or 0.0),
            sensor_bmr_conf=float(raw.get("sensor_bmr_conf", 1.0) or 1.0),
            sensor_tdee_conf=float(raw.get("sensor_tdee_conf", 1.0) or 1.0),
            activity_multiplier_w=float(raw.get("activity_multiplier_w", 1.0) or 1.0),
            neat_w=float(raw.get("neat_w", 1.0) or 1.0),
            climb_bonus_w=float(raw.get("climb_bonus_w", 1.0) or 1.0),
            n_calibrations=int(raw.get("n_calibrations", 0) or 0),
            created_at=raw.get("created_at"),
            updated_at=raw.get("updated_at"),
        )


@dataclass
class MetabolicDailySummary:
    """Aggregated daily metabolic and nutrition summary for BM2."""

    date: str
    bmr_kcal: float = 0.0
    neat_kcal: float = 0.0
    eat_kcal: float = 0.0
    climb_bonus_kcal: float = 0.0
    tdee_kcal: float = 0.0
    intake_kcal: float = 0.0
    balance_kcal: float = 0.0
    carbs_g: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    water_ml: float = 0.0
    tef_kcal: float = 0.0
    steps_estimated: int | None = None
    elevation_gain_estimated_m: float | None = None
    rides_count: int = 0
    gps_neat_kcal: float = 0.0
    metabolic_flexibility_score: float = 0.0
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "bmr_kcal": round(self.bmr_kcal, 1),
            "neat_kcal": round(self.neat_kcal, 1),
            "eat_kcal": round(self.eat_kcal, 1),
            "climb_bonus_kcal": round(self.climb_bonus_kcal, 1),
            "tdee_kcal": round(self.tdee_kcal, 1),
            "intake_kcal": round(self.intake_kcal, 1),
            "balance_kcal": round(self.balance_kcal, 1),
            "carbs_g": round(self.carbs_g, 1),
            "protein_g": round(self.protein_g, 1),
            "fat_g": round(self.fat_g, 1),
            "fiber_g": round(self.fiber_g, 1),
            "water_ml": round(self.water_ml, 0),
            "tef_kcal": round(self.tef_kcal, 1),
            "steps_estimated": self.steps_estimated,
            "elevation_gain_estimated_m": round(self.elevation_gain_estimated_m, 1)
            if self.elevation_gain_estimated_m
            else None,
            "rides_count": self.rides_count,
            "gps_neat_kcal": round(self.gps_neat_kcal, 1),
            "metabolic_flexibility_score": round(self.metabolic_flexibility_score, 2),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> MetabolicDailySummary:
        return cls(
            date=raw.get("date", ""),
            bmr_kcal=float(raw.get("bmr_kcal", 0.0) or 0.0),
            neat_kcal=float(raw.get("neat_kcal", 0.0) or 0.0),
            eat_kcal=float(raw.get("eat_kcal", 0.0) or 0.0),
            climb_bonus_kcal=float(raw.get("climb_bonus_kcal", 0.0) or 0.0),
            tdee_kcal=float(raw.get("tdee_kcal", 0.0) or 0.0),
            intake_kcal=float(raw.get("intake_kcal", 0.0) or 0.0),
            balance_kcal=float(raw.get("balance_kcal", 0.0) or 0.0),
            carbs_g=float(raw.get("carbs_g", 0.0) or 0.0),
            protein_g=float(raw.get("protein_g", 0.0) or 0.0),
            fat_g=float(raw.get("fat_g", 0.0) or 0.0),
            fiber_g=float(raw.get("fiber_g", 0.0) or 0.0),
            water_ml=float(raw.get("water_ml", 0.0) or 0.0),
            tef_kcal=float(raw.get("tef_kcal", 0.0) or 0.0),
            steps_estimated=raw.get("steps_estimated"),
            elevation_gain_estimated_m=raw.get("elevation_gain_estimated_m"),
            rides_count=int(raw.get("rides_count", 0) or 0),
            gps_neat_kcal=float(raw.get("gps_neat_kcal", 0.0) or 0.0),
            metabolic_flexibility_score=float(raw.get("metabolic_flexibility_score", 0.0) or 0.0),
            notes=raw.get("notes"),
        )


@dataclass
class Bike:
    """The bicycle and its resistance parameters."""

    weight_kg: Quantity
    crr: float = 0.005
    cda: float = 0.40
    drivetrain_efficiency: float = 0.97
    name: str = ""
    category: str = "road"
    gear_ratio: float | None = None

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> Bike:
        """Builds Bike from raw data, normalizing units."""
        if raw.get("weight") is None:
            raise ValueError("required field 'weight' missing for Bike")
        weight = t.normalize(q(raw.get("weight"), raw.get("weight_unit", "kg"), source=raw.get("source", "manual")))
        category = raw.get("category", "road")
        if category not in {"road", "gravel", "mtb", "other"}:
            raise ValueError(f"invalid bike category: {category!r}")
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
        """Serializes the bike to JSON-compatible dictionary."""
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
    def from_dict(cls, raw: dict, t: TransformerEngine) -> Bike:
        """Reconstructs Bike from serialized dictionary."""
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
    """A ride: GPS track + sensors. Metrics are computed on demand."""

    points: list[GeoPoint] = field(default_factory=list)
    title: str = ""
    sport: str = "cycling"
    laps: list[dict] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def metrics(self, t: TransformerEngine) -> dict:
        """Normalized derived metrics from the track (via Geo/Time)."""
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
    def from_raw(cls, raw: dict, t: TransformerEngine) -> Activity:
        """Builds Activity from raw GPS/sensor data."""
        gps = raw.get("gps_points") or raw.get("points")
        if not gps:
            raise ValueError("required field 'gps_points'/'points' missing for Activity")
        points = []
        for p in gps:
            ts = None
            if p.get("timestamp"):
                ts = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
            points.append(
                GeoPoint(
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
                )
            )
        return cls(
            points=points,
            title=raw.get("title", ""),
            sport=raw.get("sport", "cycling"),
            laps=raw.get("laps", []),
            segments=raw.get("segments", []),
            summary=raw.get("summary", {}),
        )

    def to_dict(self) -> dict:
        """Serializes the activity to JSON-compatible dictionary."""
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
    def from_dict(cls, raw: dict, t: TransformerEngine) -> Activity:
        """Reconstructs Activity from serialized dictionary."""
        points = []
        for p in raw.get("points", []):
            ts = None
            if p.get("timestamp"):
                ts = datetime.fromisoformat(p["timestamp"])
            points.append(
                GeoPoint(
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
                )
            )
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
    """The territory traversed by the activity."""

    surface: str = "asphalt"
    roughness_index: Quantity = field(default_factory=lambda: q(0.0, "", source="manual"))
    avg_slope_percent: Quantity | None = None
    wind_speed_ms: Quantity | None = None
    temperature_c: Quantity | None = None

    @classmethod
    def from_raw(cls, raw: dict, t: TransformerEngine) -> WorldObject:
        """Builds WorldObject from raw environment data."""
        slope = None
        if raw.get("avg_slope") is not None:
            slope = t.normalize(q(raw["avg_slope"], raw.get("avg_slope_unit", "%"), source=raw.get("source", "dem")))
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
        """Serializes the world object to JSON-compatible dictionary."""
        return {
            "surface": self.surface,
            "roughness_index": _quantity_to_dict(self.roughness_index),
            "avg_slope_percent": _quantity_to_dict(self.avg_slope_percent) if self.avg_slope_percent else None,
            "wind_speed_ms": _quantity_to_dict(self.wind_speed_ms) if self.wind_speed_ms else None,
            "temperature_c": _quantity_to_dict(self.temperature_c) if self.temperature_c else None,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> WorldObject:
        """Reconstructs WorldObject from serialized dictionary."""
        return cls(
            surface=raw.get("surface", "asphalt"),
            roughness_index=_quantity_from_dict(raw["roughness_index"], t),
            avg_slope_percent=_quantity_from_dict(raw["avg_slope_percent"], t)
            if raw.get("avg_slope_percent")
            else None,
            wind_speed_ms=_quantity_from_dict(raw["wind_speed_ms"], t) if raw.get("wind_speed_ms") else None,
            temperature_c=_quantity_from_dict(raw["temperature_c"], t) if raw.get("temperature_c") else None,
        )


@dataclass
class AnalysisContext:
    """Complete context passed to Model Engine algorithms."""

    athlete: Athlete
    activity: Activity
    bike: Bike
    world: WorldObject
    transformer: TransformerEngine
    metabolic_profile: MetabolicProfile | None = None

    @property
    def total_mass_kg(self) -> float:
        """Total mass (athlete + bike) in kg, ready for power calculations."""
        return self.athlete.weight_kg.value + self.bike.weight_kg.value

    def to_dict(self) -> dict:
        """Serializes the complete context to JSON-compatible dictionary."""
        return {
            "athlete": self.athlete.to_dict(),
            "activity": self.activity.to_dict(),
            "bike": self.bike.to_dict(),
            "world": self.world.to_dict(),
            "metabolic_profile": self.metabolic_profile.to_dict() if self.metabolic_profile else None,
        }

    @classmethod
    def from_dict(cls, raw: dict, t: TransformerEngine) -> AnalysisContext:
        """Reconstructs AnalysisContext from serialized dictionary."""
        mp = raw.get("metabolic_profile")
        return cls(
            athlete=Athlete.from_dict(raw["athlete"], t),
            activity=Activity.from_dict(raw["activity"], t),
            bike=Bike.from_dict(raw["bike"], t),
            world=WorldObject.from_dict(raw["world"], t),
            transformer=t,
            metabolic_profile=MetabolicProfile.from_dict(mp) if mp else None,
        )
