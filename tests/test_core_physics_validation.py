"""Test del validation layer fisico contro dati power-meter simulati."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from bike_analyzer.core.models import GPSPoint, Ride, haversine_distance_m
from bike_analyzer.core.physics import (
    RiderBikeParams,
    grade_between,
    instantaneous_power,
    validate_ride_power,
)


def _build_self_consistent_ride(n=7, params=None, noise=0.0):
    pts = []
    ts0 = datetime(2026, 7, 10, 8, 0, 0)
    for i in range(n):
        pts.append(GPSPoint(
            lat=45.0 + 0.001 * i, lon=9.0, altitude=100.0 + 5.0 * i,
            timestamp=ts0 + timedelta(seconds=10 * i), power=None,
        ))
    for i in range(1, n):
        ds = haversine_distance_m(pts[i - 1].lat, pts[i - 1].lon, pts[i].lat, pts[i].lon)
        v = ds / 10.0
        g = grade_between(pts[i - 1], pts[i])
        p = instantaneous_power(v, g, params)
        p += noise * (1.0 if i % 2 else -1.0)
        pts[i] = replace(pts[i], power=p)
    return Ride(id=1, gps_points=pts, weight_kg=70.0)


def test_self_consistent_ride_has_near_zero_error():
    params = RiderBikeParams(rider_mass_kg=70.0, bike_mass_kg=8.0)
    ride = _build_self_consistent_ride(n=7, params=params)
    res = validate_ride_power(ride, params)
    assert res is not None
    assert res.n_points == 6
    assert res.mae_w < 1e-6
    assert res.bias_w < 1e-6
    assert res.r2 > 0.99


def test_noisy_ride_has_positive_mae():
    params = RiderBikeParams(rider_mass_kg=70.0, bike_mass_kg=8.0)
    ride = _build_self_consistent_ride(n=7, params=params, noise=10.0)
    res = validate_ride_power(ride, params)
    assert res is not None
    assert res.mae_w > 0.0
    assert res.r2 < 1.0


def test_wrong_cda_produces_systematic_bias():
    truth = RiderBikeParams(rider_mass_kg=70.0, bike_mass_kg=8.0, cda=0.30)
    ride = _build_self_consistent_ride(n=7, params=truth)
    wrong = RiderBikeParams(rider_mass_kg=70.0, bike_mass_kg=8.0, cda=0.45)
    res = validate_ride_power(ride, wrong)
    assert res is not None
    # CdA più alto -> potenza stimata sistematicamente sovrastimata
    assert res.bias_w > 0.0


def test_insufficient_power_data_returns_none():
    ride = Ride(id=1, gps_points=[
        GPSPoint(lat=45.0, lon=9.0, altitude=100.0,
                 timestamp=datetime(2026, 7, 10, 8, 0, 0), power=None),
        GPSPoint(lat=45.001, lon=9.0, altitude=105.0,
                 timestamp=datetime(2026, 7, 10, 8, 0, 10), power=200.0),
    ])
    assert validate_ride_power(ride) is None


def test_ride_without_points_returns_none():
    assert validate_ride_power(Ride(id=1, gps_points=[])) is None
