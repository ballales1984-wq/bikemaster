"""Test BikeMaster 2.0 - unità di misura e transformer."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from bike_analyzer.bm2 import TransformerEngine, q
from bike_analyzer.bm2.transformer import GeoPoint
from bike_analyzer.bm2.units import UnitError, UnitRegistry, convert, default_registry


def test_mass_conversion_lb_to_kg():
    out = convert(q(154.0, "lb", source="manual"), "kg")
    assert out.value == pytest.approx(69.85, abs=0.05)
    assert out.unit == "kg"


def test_length_and_speed_conversions():
    assert convert(q(1.0, "km"), "m").value == pytest.approx(1000.0)
    assert convert(q(3.6, "km/h"), "m/s").value == pytest.approx(1.0)
    assert convert(q(10.0, "m/s"), "km/h").value == pytest.approx(36.0)


def test_energy_conversion_kcal_to_j():
    out = convert(q(1.0, "kcal"), "J")
    assert out.value == pytest.approx(4184.0)


def test_temperature_offset_conversion():
    c = convert(q(32.0, "°F"), "°C")
    assert c.value == pytest.approx(0.0)
    k = convert(q(0.0, "°C"), "K")
    assert k.value == pytest.approx(273.15)


def test_slope_percent_to_degree():
    deg = convert(q(100.0, "%"), "deg")
    assert deg.value == pytest.approx(45.0, abs=0.1)


def test_slope_nonlinear_uncertainty():
    qty = q(100.0, "%", precision=1.0, source="dem")
    deg = convert(qty, "deg")
    assert deg.value == pytest.approx(45.0, abs=0.1)
    assert deg.precision > 0
    assert deg.precision == pytest.approx(0.286, abs=0.01)
    back = convert(deg, "%")
    assert back.value == pytest.approx(100.0, abs=0.5)
    assert back.precision > 0


def test_incompatible_dimensions_raise():
    with pytest.raises(UnitError):
        convert(q(10.0, "kg"), "m")


def test_transformer_normalizes_to_canonical():
    t = TransformerEngine()
    out = t.normalize(q(154.0, "lb", source="manual"))
    assert out.unit == "kg"
    assert out.precision > 0


def test_geo_track_metrics():
    t = TransformerEngine()
    pts = [
        GeoPoint(45.0, 9.0, altitude=250, timestamp=datetime(2026, 7, 10, 8, 0, 0, tzinfo=UTC)),
        GeoPoint(45.001, 9.001, altitude=290, timestamp=datetime(2026, 7, 10, 8, 10, 0, tzinfo=UTC)),
        GeoPoint(45.002, 9.002, altitude=330, timestamp=datetime(2026, 7, 10, 8, 20, 0, tzinfo=UTC)),
    ]
    m = t.geo.track_metrics(pts)
    assert m["distance_m"] > 0
    assert m["gain_m"] == pytest.approx(80.0, abs=1.0)
    assert m["avg_slope_percent"] > 0
    dur = t.time.duration_from_points(pts)
    assert dur == pytest.approx(1200.0)


def test_data_quality_range_check():
    t = TransformerEngine()
    bad = q(500.0, "bpm", source="hr_band")
    assert not t.quality.in_range(bad)
    assert t.quality.check(bad)


def test_pressure_conversions():
    registry = UnitRegistry()
    assert registry.convert(q(1.0, "atm"), "Pa").value == pytest.approx(101325.0)
    assert registry.convert(q(760.0, "mmHg"), "hPa").value == pytest.approx(1013.25, abs=0.01)
    assert registry.convert(q(1.0, "bar"), "Pa").value == pytest.approx(100000.0)
    assert registry.convert(q(1013.25, "hPa"), "mmHg").value == pytest.approx(760.0, abs=0.1)


def test_density_conversions():
    registry = UnitRegistry()
    assert registry.convert(q(1.0, "kg/m^3"), "g/L").value == pytest.approx(1.0)
    assert registry.convert(q(1.225, "g/L"), "kg/m^3").value == pytest.approx(1.225)


def test_torque_conversions():
    registry = UnitRegistry()
    assert registry.convert(q(1.0, "kNm"), "Nm").value == pytest.approx(1000.0)


def test_imperial_length_conversions():
    registry = UnitRegistry()
    assert registry.convert(q(1.0, "mi"), "m").value == pytest.approx(1609.344)
    assert registry.convert(q(5280.0, "ft"), "m").value == pytest.approx(1609.344, abs=0.001)
    assert registry.convert(q(1000.0, "m"), "ft").value == pytest.approx(3280.84, abs=0.01)


def test_explain_conversion():
    steps = default_registry.explain_conversion(q(1.0, "km"), "m")
    assert any("Factor to canonical" in s for s in steps)
    assert any("Factor from canonical" in s for s in steps)
    temp_steps = default_registry.explain_conversion(q(32.0, "°F"), "°C")
    assert any("Intermediate step: Kelvin" in s for s in temp_steps)
    slope_steps = default_registry.explain_conversion(q(100.0, "%"), "deg")
    assert any("Non-linear conversion" in s for s in slope_steps)
    bad_steps = default_registry.explain_conversion(q(10.0, "kg"), "m")
    assert any("ERROR: incompatible dimensions" in s for s in bad_steps)


def test_power_to_weight():
    t = TransformerEngine()
    pw = q(200.0, "W", precision=2.0, source="power_meter")
    wt = q(70.0, "kg", precision=0.1, source="scale")
    ratio = t.power_to_weight(pw, wt)
    assert ratio.value == pytest.approx(200.0 / 70.0, abs=1e-6)
    assert ratio.unit == "W/kg"
    assert ratio.precision > 0
    assert ratio.precision == pytest.approx(
        abs(200.0 / 70.0) * math.sqrt((2.0 / 200.0) ** 2 + (0.1 / 70.0) ** 2),
        abs=1e-6,
    )


def test_air_density():
    t = TransformerEngine()
    temp = q(20.0, "°C", precision=0.5, source="manual")
    pressure = q(1013.25, "hPa", precision=1.0, source="manual")
    rho = t.air_density(temp, pressure)
    expected = 101325.0 / (287.05 * (20.0 + 273.15))
    assert rho.value == pytest.approx(expected, abs=1e-4)
    assert rho.unit == "kg/m^3"
    assert rho.precision > 0


def test_data_quality_new_ranges():
    t = TransformerEngine()
    assert not t.quality.in_range(q(31.0, "W/kg", source="power_meter"))
    assert t.quality.in_range(q(5.0, "W/kg", source="power_meter"))
    assert not t.quality.in_range(q(101.0, "Nm", source="manual"))
    assert t.quality.in_range(q(10.0, "Nm", source="manual"))
    assert not t.quality.in_range(q(299.0, "mmHg", source="manual"))
    assert t.quality.in_range(q(760.0, "mmHg", source="manual"))
    assert not t.quality.in_range(q(2.1, "g/L", source="manual"))
    assert t.quality.in_range(q(1.2, "g/L", source="manual"))


def test_data_quality_temporal():
    t = TransformerEngine()
    base = datetime(2026, 7, 10, 8, 0, 0, tzinfo=UTC)
    ok = [
        q(1.0, "W", timestamp=base),
        q(2.0, "W", timestamp=base + timedelta(seconds=10)),
        q(3.0, "W", timestamp=base + timedelta(seconds=20)),
    ]
    assert t.quality.check_temporal(ok) == []
    bad = [
        q(1.0, "W", timestamp=base + timedelta(seconds=20)),
        q(2.0, "W", timestamp=base),
    ]
    problems = t.quality.check_temporal(bad)
    assert any("timestamp non ordinate" in p for p in problems)
    gap = [
        q(1.0, "W", timestamp=base),
        q(2.0, "W", timestamp=base + timedelta(seconds=7201)),
    ]
    problems = t.quality.check_temporal(gap, max_gap_seconds=3600.0)
    assert any("salto temporale" in p for p in problems)
