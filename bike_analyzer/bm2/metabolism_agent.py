"""BikeMaster 2.0 - Metabolism Agent.

Transforms raw athlete data, activity tracking and food logs into BM2 Core
Model objects (MetabolicProfile, MetabolicDailySummary) already normalized
via the Transformer Engine. Algorithms never see raw data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .models import Activity, Athlete, MetabolicDailySummary, MetabolicProfile, WorldObject
from .transformer import GeoPoint, TransformerEngine

__all__ = ["MetabolismAgent"]


class MetabolismAgent:
    """Manages metabolic data (athlete body composition, energy expenditure, food logs).

    Transforms raw athlete + tracking + nutrition data into Core Model
    ``MetabolicProfile`` and ``MetabolicDailySummary`` objects, normalizing
    units via the Transformer Engine.
    """

    def __init__(self, transformer: TransformerEngine) -> None:
        """Initializes with the TransformerEngine for normalization.

        Args:
            transformer: Unit transformation engine.
        """
        self.t = transformer

    def collect_profile(self, raw: dict) -> MetabolicProfile:
        """Builds a ``MetabolicProfile`` from raw athlete data.

        Args:
            raw: Dictionary with athlete metabolic data (weight, height, age,
                 fat_percentage, sex, bmr_formula, activity_level).

        Returns:
            MetabolicProfile with computed BMR/TDEE/NEAT/EAT.
        """
        from .algorithms.metabolism import MetabolismModel
        athlete = Athlete.from_raw(raw, self.t)
        Athlete.from_raw(raw, self.t)
        bike_raw = {"weight": raw.get("weight", 70.0), "weight_unit": "kg",
                     "crr": 0.005, "cda": 0.40, "drivetrain_efficiency": 0.97}
        from .models import Bike
        bike_obj = Bike.from_raw(bike_raw, self.t)
        activity = Activity(points=[])
        world = WorldObject()
        ctx = type("Ctx", (), {
            "athlete": athlete,
            "activity": activity,
            "bike": bike_obj,
            "world": world,
            "transformer": self.t,
            "metabolic_profile": None,
        })()
        algo = MetabolismModel()
        result = algo.run(ctx)
        profile_data = result.details.get("metabolic_profile", {})
        return MetabolicProfile.from_dict(profile_data)

    def collect_daily_summary(self, raw: dict, activity: Activity | None = None,
                               date: str = "") -> MetabolicDailySummary:
        """Builds a ``MetabolicDailySummary`` from raw tracking + nutrition data.

        Args:
            raw: Dictionary with daily nutrition (intake_kcal, carbs_g,
                 protein_g, fat_g, fiber_g, water_ml) and optional ride data.
            activity: Optional Activity with GPS/sensor data for EAT/NEAT.
            date: ISO date string (YYYY-MM-DD).

        Returns:
            MetabolicDailySummary with all computed components.
        """
        from .algorithms.metabolism import MetabolismModel

        athlete_raw = raw.get("athlete", {})
        athlete = Athlete.from_raw(athlete_raw, self.t)
        bike_raw = raw.get("bike", {"weight": athlete_raw.get("weight", 70.0),
                                     "weight_unit": "kg",
                                     "crr": 0.005, "cda": 0.40,
                                     "drivetrain_efficiency": 0.97})
        from .models import Bike
        bike_obj = Bike.from_raw(bike_raw, self.t)

        act = activity or Activity(points=[])
        world = WorldObject()
        mp_raw = raw.get("metabolic_profile")
        mp = MetabolicProfile.from_dict(mp_raw) if mp_raw else None
        ctx = type("Ctx", (), {
            "athlete": athlete,
            "activity": act,
            "bike": bike_obj,
            "world": world,
            "transformer": self.t,
            "metabolic_profile": mp,
        })()
        algo = MetabolismModel()
        return algo.build_daily_summary(
            ctx, date,
            intake_kcal=float(raw.get("intake_kcal", 0.0) or 0.0),
            carbs_g=float(raw.get("carbs_g", 0.0) or 0.0),
            protein_g=float(raw.get("protein_g", 0.0) or 0.0),
            fat_g=float(raw.get("fat_g", 0.0) or 0.0),
            fiber_g=float(raw.get("fiber_g", 0.0) or 0.0),
            water_ml=float(raw.get("water_ml", 0.0) or 0.0),
        )

    def from_ride(self, ride: dict, athlete_raw: dict) -> MetabolicDailySummary:
        """Builds a ``MetabolicDailySummary`` from a single ride dict.

        Args:
            ride: Dictionary with ride data (elevation_gain_m, gps_points,
                  calories, duration_s).
            athlete_raw: Raw athlete data dict.

        Returns:
            MetabolicDailySummary with ride calories as EAT.
        """
        gps_points = []
        for p in (ride.get("gps_points") or ride.get("points") or []):
            ts = p.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = None
            elif isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts, tz=UTC)
            gps_points.append(GeoPoint(
                lat=float(p.get("lat", 0.0)),
                lon=float(p.get("lon", 0.0)),
                altitude=float(p.get("altitude", 0.0)),
                timestamp=ts,
                x=0.0, y=0.0,
                speed=p.get("speed"),
            ))

        date_str = ""
        if gps_points and gps_points[0].timestamp:
            date_str = gps_points[0].timestamp.date().isoformat()
        elif ride.get("date"):
            date_str = str(ride.get("date"))

        act = Activity(points=gps_points, title=ride.get("title", ""),
                       summary={"elevation_gain_m": ride.get("elevation_gain_m"),
                                "calories": ride.get("calories")})
        raw = {"athlete": athlete_raw}
        return self.collect_daily_summary(raw, activity=act, date=date_str)
