"""Test BikeMaster 2.0 - modelli di dominio (models.py)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow
from datetime import datetime, timezone

from bike_analyzer.bm2 import Athlete, Bike, Activity, WorldObject, AnalysisContext, q, TransformerEngine
from bike_analyzer.bm2.transformer import GeoPoint


def _t():
    return TransformerEngine()


def test_athlete_from_raw_with_validation():
    t = _t()
    raw = {
        "weight": 75.0,
        "age": 34,
        "height": 1.80,
        "ftp": 280.0,
        "max_hr": 185,
        "resting_hr": 55,
        "experience_level": "Advanced",
        "weekly_hours": 10.0,
        "name": "Mario",
        "ctl": 95.0,
        "atl": 80.0,
        "tsb": 15.0,
    }
    a = Athlete.from_raw(raw, t)
    assert a.weight_kg.value == 75.0
    assert a.age == 34
    assert a.height_m.value == 1.80
    assert a.ftp_w.value == 280.0
    assert a.max_hr_bpm.value == 185.0
    assert a.resting_hr_bpm.value == 55.0
    assert a.experience_level == "Advanced"
    assert a.weekly_hours.value == 36000.0
    assert a.name == "Mario"
    assert a.ctl_stress_score.value == 95.0
    assert a.atl_stress_score.value == 80.0
    assert a.tsb_stress_score.value == 15.0


def test_athlete_from_raw_missing_weight_raises():
    t = _t()
    with pytest.raises(ValueError, match="weight"):
        Athlete.from_raw({"age": 30}, t)


def test_athlete_power_to_weight():
    t = _t()
    a = Athlete(weight_kg=q(70.0, "kg"), ftp_w=q(280.0, "W"))
    assert a.power_to_weight() == 4.0
    b = Athlete(weight_kg=q(70.0, "kg"))
    assert a.power_to_weight() != 0.0
    assert b.power_to_weight() is None


def test_bike_from_raw_with_category_and_gear():
    t = _t()
    raw = {
        "weight": 8.5,
        "category": "gravel",
        "gear_ratio": 2.75,
        "crr": 0.008,
        "cda": 0.42,
        "name": "Gravelx",
    }
    b = Bike.from_raw(raw, t)
    assert b.weight_kg.value == 8.5
    assert b.category == "gravel"
    assert b.gear_ratio == 2.75
    assert b.crr == 0.008
    assert b.name == "Gravelx"


def test_bike_from_raw_invalid_category_raises():
    t = _t()
    with pytest.raises(ValueError, match="invalid bike category"):
        Bike.from_raw({"weight": 8.0, "category": "unknown"}, t)


def test_bike_from_raw_missing_weight_raises():
    t = _t()
    with pytest.raises(ValueError, match="weight"):
        Bike.from_raw({"category": "mtb"}, t)


def test_activity_from_raw_with_laps_segments_summary():
    t = _t()
    raw = {
        "gps_points": [
            {"lat": 45.0, "lon": 9.0, "altitude": 200, "timestamp": "2026-07-10T08:00:00Z"},
            {"lat": 45.001, "lon": 9.001, "altitude": 210, "timestamp": "2026-07-10T08:10:00Z"},
        ],
        "title": "Test Ride",
        "sport": "cycling",
        "laps": [{"start": "08:00", "end": "08:10", "distance_m": 1200}],
        "segments": [{"name": "Sprint", "type": "short"}],
        "summary": {"avg_hr": 145},
    }
    act = Activity.from_raw(raw, t)
    assert len(act.points) == 2
    assert act.title == "Test Ride"
    assert act.sport == "cycling"
    assert len(act.laps) == 1
    assert act.laps[0]["distance_m"] == 1200
    assert len(act.segments) == 1
    assert act.summary["avg_hr"] == 145


def test_activity_from_raw_missing_points_raises():
    t = _t()
    with pytest.raises(ValueError, match="gps_points"):
        Activity.from_raw({"title": "No points"}, t)


def test_activity_metrics_preserved():
    t = _t()
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.005, 9.005, 360, datetime(2026, 7, 10, 9, 0, 0, tzinfo=timezone.utc)),
    ]
    act = Activity(points=pts)
    m = act.metrics(t)
    assert "distance_m" in m
    assert "duration_s" in m
    assert "gain_m" in m
    assert "loss_m" in m
    assert "avg_slope_percent" in m
    assert "avg_speed_ms" in m


def test_world_object_roundtrip():
    t = _t()
    w = WorldObject(
        surface="gravel",
        roughness_index=q(0.3, "", source="manual"),
        avg_slope_percent=t.normalize(q(4.0, "%", source="dem")),
        wind_speed_ms=q(2.5, "m/s", source="manual"),
        temperature_c=q(22.0, "°C", source="manual"),
    )
    d = w.to_dict()
    w2 = WorldObject.from_dict(d, t)
    assert w2.surface == "gravel"
    assert w2.roughness_index.value == 0.3
    assert w2.avg_slope_percent.value == 4.0
    assert w2.wind_speed_ms.value == 2.5
    assert w2.temperature_c.value == 22.0


def test_athlete_roundtrip_preserves_quantities():
    t = _t()
    a = Athlete(
        weight_kg=q(75.0, "kg"),
        height_m=q(1.85, "m"),
        ftp_w=q(300.0, "W"),
        max_hr_bpm=q(190.0, "bpm"),
        resting_hr_bpm=q(50.0, "bpm"),
        weekly_hours=q(8.0, "h"),
        experience_level="Elite",
        ctl_stress_score=q(110.0, "stress_score"),
    )
    d = a.to_dict()
    a2 = Athlete.from_dict(d, t)
    assert a2.weight_kg.value == 75.0
    assert a2.weight_kg.unit == "kg"
    assert a2.height_m.value == 1.85
    assert a2.ftp_w.value == 300.0
    assert a2.ctl_stress_score.value == 110.0


def test_bike_roundtrip_preserves_quantities():
    t = _t()
    b = Bike(
        weight_kg=q(7.8, "kg"),
        category="mtb",
        gear_ratio=2.4,
        crr=0.010,
        cda=0.45,
        name="Trail",
    )
    d = b.to_dict()
    b2 = Bike.from_dict(d, t)
    assert b2.weight_kg.value == 7.8
    assert b2.category == "mtb"
    assert b2.gear_ratio == 2.4
    assert b2.crr == 0.010


def test_activity_roundtrip_preserves_points():
    t = _t()
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.001, 9.001, 210, datetime(2026, 7, 10, 8, 10, 0, tzinfo=timezone.utc)),
    ]
    act = Activity(points=pts, title="RT", laps=[{"dist": 1.0}])
    d = act.to_dict()
    act2 = Activity.from_dict(d, t)
    assert len(act2.points) == 2
    assert act2.points[0].lat == 45.0
    assert act2.title == "RT"
    assert act2.laps[0]["dist"] == 1.0


def test_analysis_context_roundtrip():
    t = _t()
    athlete = Athlete(weight_kg=q(72.0, "kg"), age=28)
    bike = Bike(weight_kg=q(8.2, "kg"), category="road")
    pts = [
        GeoPoint(45.0, 9.0, 200, datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)),
        GeoPoint(45.001, 9.001, 210, datetime(2026, 7, 10, 8, 10, 0, tzinfo=timezone.utc)),
    ]
    activity = Activity(points=pts)
    world = WorldObject(surface="asphalt")
    ctx = AnalysisContext(athlete=athlete, activity=activity, bike=bike, world=world, transformer=t)
    d = ctx.to_dict()
    ctx2 = AnalysisContext.from_dict(d, t)
    assert ctx2.athlete.weight_kg.value == 72.0
    assert ctx2.bike.category == "road"
    assert len(ctx2.activity.points) == 2
    assert ctx2.world.surface == "asphalt"
