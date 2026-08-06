"""Test adapter prodotto (Ride/AthleteProfile) -> contesto bm2."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bike_analyzer.bm2 import SimulationEngine
from bike_analyzer.bm2.adapters import ride_to_analysis_context, ride_to_bm2_raw
from bike_analyzer.bm2.algorithms import ALL_ALGORITHMS
from bike_analyzer.bm2.models import AnalysisContext
from bike_analyzer.bm2.simulation import ScenarioOverride
from bike_analyzer.core.models import AthleteProfile, GPSPoint, Ride


def _ride():
    pts = [
        GPSPoint(lat=45.0, lon=9.0, altitude=200.0, timestamp=datetime(2026, 7, 10, 8, 0, 0, tzinfo=UTC)),
        GPSPoint(lat=45.005, lon=9.005, altitude=360.0, timestamp=datetime(2026, 7, 10, 9, 0, 0, tzinfo=UTC)),
    ]
    return Ride(
        id=1, athlete_id=1, distance_km=12.0, duration_minutes=60.0,
        avg_speed_kmh=12.0, weight_kg=75.0, elevation_gain_m=160.0, gps_points=pts,
    )


def _athlete():
    return AthleteProfile(id=1, age=34, weight_kg=75.0, ftp_watts=250.0,
                          experience_level="Intermediate", height_cm=180.0)


def test_ride_without_gps_points_raises():
    r = Ride(id=1, distance_km=10.0, weight_kg=70.0, gps_points=[])
    with pytest.raises(ValueError):
        ride_to_bm2_raw(r)


def test_raw_maps_weight_and_ftp():
    raw = ride_to_bm2_raw(_ride(), _athlete())
    assert raw["athlete"]["weight"] == 75.0
    assert raw["athlete"]["ftp"] == 250.0
    assert raw["athlete"]["experience_level"] == "Intermediate"
    assert raw["bike"]["weight"] == 8.0
    assert len(raw["gps_points"]) == 2


def test_raw_derives_avg_slope_from_ride():
    raw = ride_to_bm2_raw(_ride())
    # 160 m / 12000 m = 1.33%
    assert raw["world"]["avg_slope"] == pytest.approx(1.333, abs=0.01)


def test_analysis_context_builds_from_ride():
    ctx = ride_to_analysis_context(_ride(), _athlete())
    assert isinstance(ctx, AnalysisContext)
    assert ctx.total_mass_kg == pytest.approx(83.0)
    # la traccia ha dislivello -> pendenza disponibile
    assert ctx.world.avg_slope_percent is not None


def test_simulation_runs_on_real_ride():
    ctx = ride_to_analysis_context(_ride(), _athlete())
    engine = SimulationEngine(ALL_ALGORITHMS)
    comp = engine.compare(ctx, ScenarioOverride(athlete_weight_delta_kg=-5.0))
    assert "EnergyModel" in comp.baseline and "EnergyModel" in comp.scenario
    assert comp.deltas
    assert comp.scenario["EnergyModel"].value < comp.baseline["EnergyModel"].value
