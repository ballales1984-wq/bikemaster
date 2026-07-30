"""BikeMaster 2.0 — Physics validation demo against synthetic power-meter data.

Eseguibile con::

    cd bike_analyzer
    python -m bm2.simulation.validate_demo

Genera 12 ride sintetiche con profili di velocità/pendenza variabili,
crea potenze "misurate" a partire dal modello fisico con rumore realistico,
poi valida il kernel BM2 confrontando stime vs misure. Stampa metriche
aggregate (MAE, RMSE, R², bias).
"""

from __future__ import annotations

import math
import random
import statistics
from datetime import datetime, timedelta
from typing import Sequence

from ..algorithms.power_model import PowerModel
from ..models import Activity, AnalysisContext, Athlete, Bike, GeoPoint, WorldObject
from ..simulation import ScenarioOverride, SimulationEngine
from ..transformer import TransformerEngine
from ..units import q
from bike_analyzer.core.physics.validation import validate_ride_power
from bike_analyzer.core.models import GPSPoint, Ride
from bike_analyzer.core.physics.constants import RiderBikeParams
from bike_analyzer.core.physics.power import instantaneous_power


def _random_params(rng: random.Random) -> tuple[Athlete, Bike, WorldObject, float]:
    weight_kg = rng.uniform(62, 82)
    bike_kg = rng.uniform(6.5, 9.5)
    ftp_w = rng.uniform(180, 300)
    slope = rng.uniform(-1.0, 5.0)
    surface = rng.choice(["asphalt", "asphalt", "asphalt", "gravel"])
    return (
        Athlete(weight_kg=q(weight_kg, "kg"), ftp_w=q(ftp_w, "W")),
        Bike(weight_kg=q(bike_kg, "kg")),
        WorldObject(avg_slope_percent=q(slope, "%"), surface=surface),
        slope,
    )


def _build_ride(
    ride_id: int,
    rng: random.Random,
    n_points: int = 50,
) -> tuple[Ride, RiderBikeParams]:
    athlete, bike, world, base_slope = _random_params(rng)
    transformer = TransformerEngine()

    t0 = datetime(2024, 1, 1, 10, 0, 0)
    lat = 45.0 + ride_id * 0.01
    lon = 7.0 + ride_id * 0.01

    base_speed_ms = rng.uniform(4.0, 9.0)
    dt = 1.0
    gps_points: list[GPSPoint] = []
    cur_lat = lat
    cur_lon = lon
    cur_alt = 100.0
    for i in range(n_points):
        speed = base_speed_ms * rng.uniform(0.85, 1.15)
        slope = base_slope + rng.uniform(-1.5, 1.5)
        grade = slope / 100.0
        ds = speed * dt
        dlat = ds / 111_320.0
        dalt = grade * ds

        params = RiderBikeParams(
            rider_mass_kg=athlete.weight_kg.value,
            bike_mass_kg=bike.weight_kg.value,
            cda=0.40,
            crr=0.005,
            drivetrain_efficiency=0.97,
        )
        estimated = instantaneous_power(speed, grade, params, wind_ms=0.0)
        measured = estimated * rng.uniform(0.90, 1.10)

        cur_lat += dlat
        cur_alt += dalt
        gps_points.append(
            GPSPoint(
                lat=cur_lat,
                lon=cur_lon,
                altitude=cur_alt,
                timestamp=t0 + timedelta(seconds=i * dt),
                speed=speed,
                power=measured,
            )
        )

    total_dist_m = sum(
        __import__("bike_analyzer.core.models", fromlist=["haversine_distance_m"]).haversine_distance_m(
            gps_points[i].lat, gps_points[i].lon,
            gps_points[i + 1].lat, gps_points[i + 1].lon,
        )
        for i in range(len(gps_points) - 1)
    )
    total_dur_s = sum(
        (gps_points[i + 1].timestamp - gps_points[i].timestamp).total_seconds()
        for i in range(len(gps_points) - 1)
    )

    ride = Ride(
        id=ride_id,
        athlete_id=1,
        tenant_id=1,
        distance_km=round(total_dist_m / 1000.0, 3),
        duration_minutes=round(total_dur_s / 60.0, 1),
        avg_speed_kmh=round((total_dist_m / total_dur_s) * 3.6, 1) if total_dur_s > 0 else 0.0,
        gps_points=gps_points,
    )
    return ride, params


def _summarize(results: Sequence[dict]) -> dict:
    def _avg(key: str) -> float:
        vals = [r[key] for r in results if key in r]
        return sum(vals) / len(vals) if vals else 0.0

    return {
        "rides_validated": len(results),
        "avg_n_points": _avg("n_points"),
        "avg_mae_w": _avg("mae_w"),
        "avg_rmse_w": _avg("rmse_w"),
        "avg_bias_w": _avg("bias_w"),
        "avg_r2": _avg("r2"),
        "avg_mean_measured_w": _avg("mean_measured_w"),
        "avg_mean_estimated_w": _avg("mean_estimated_w"),
    }


def main() -> None:
    rng = random.Random(42)
    results: list[dict] = []
    for ride_id in range(1, 13):
        ride, params = _build_ride(ride_id, rng)
        res = validate_ride_power(ride, params)
        if res is None:
            continue
        results.append(res.to_dict())

    print("=== BM2 Physics Validation (synthetic power-meter) ===\n")
    if not results:
        print("No ride had enough power-meter data.")
        return

    for i, r in enumerate(results, 1):
        print(
            f"Ride {i:02d}: n={r['n_points']:3d} | "
            f"MAE={r['mae_w']:6.2f} W | RMSE={r['rmse_w']:6.2f} W | "
            f"bias={r['bias_w']:6.2f} W | R²={r['r2']:.3f}"
        )

    summary = _summarize(results)
    print("\n--- Aggregate ---")
    for k, v in summary.items():
        print(f"{k}: {v}")

    avg_r2 = summary["avg_r2"]
    if avg_r2 >= 0.85:
        print("\nValidation: PASS (R² >= 0.85)")
    elif avg_r2 >= 0.70:
        print("\nValidation: MARGINAL (0.70 <= R² < 0.85)")
    else:
        print("\nValidation: FAIL (R² < 0.70)")


if __name__ == "__main__":
    main()
