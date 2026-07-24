"""Tests for aethermap.data.analytics (Fase 2 analytics layer)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from aethermap.ai.models import Oggetto, Posizione, Stato
from aethermap.data.analytics import (
    h3_grid_aggregation,
    latest_state_by_object,
    objects_in_timerange,
    radius_summary,
    spatial_density_by_s2,
    spatial_density_by_type,
    temporal_field_trend,
)
from aethermap.data.store import SpatialStore

# ===========================================================================
# Helpers
# ===========================================================================


def _make_obj(oid, lat=45.0, lon=9.0, tipo="strada"):
    return Oggetto(id=oid, tipo=tipo, posizione=Posizione.from_latlon(lat, lon))


def _build_world(n=5):
    store = SpatialStore()
    for i in range(n):
        tipo = "strada" if i % 2 == 0 else "albero"
        store.add(_make_obj(f"o{i}", 45.0 + i * 0.001, 9.0 + i * 0.001, tipo))
    return store


# ===========================================================================
# spatial_density_by_s2
# ===========================================================================


class TestSpatialDensityByS2:
    def test_returns_counts(self):
        store = _build_world(4)
        density = spatial_density_by_s2(store.all())
        assert isinstance(density, dict)

    def test_non_empty_counts(self):
        store = _build_world(3)
        density = spatial_density_by_s2(store.all())
        vals = [v for v in density.values() if v > 0]
        assert len(vals) >= 1

    def test_sum_equals_n_objects(self):
        n = 5
        store = _build_world(n)
        density = spatial_density_by_s2(store.all())
        total = sum(v for k, v in density.items() if k != "unknown")
        assert total == n


# ===========================================================================
# spatial_density_by_type
# ===========================================================================


class TestSpatialDensityByType:
    def test_counts_by_type(self):
        store = _build_world(4)
        density = spatial_density_by_type(store.all())
        assert "strada" in density
        assert "albero" in density

    def test_total_sum(self):
        n = 6
        store = _build_world(n)
        density = spatial_density_by_type(store.all())
        assert sum(density.values()) == n


# ===========================================================================
# radius_summary
# ===========================================================================


class TestRadiusSummary:
    def test_returns_type_counts_for_nearby(self):
        store = _build_world(6)
        summary = radius_summary(store.all(), 45.0, 9.0, 1000.0)
        assert isinstance(summary, dict)

    def test_large_radius_includes_all(self):
        store = _build_world(6)
        summary = radius_summary(store.all(), 45.0, 9.0, 1_000_000.0)
        assert sum(summary.values()) == 6

    def test_small_radius_excludes_far(self):
        store = _build_world(6)
        summary = radius_summary(store.all(), 45.0, 9.0, 50.0)
        assert sum(summary.values()) >= 1
        assert sum(summary.values()) < 6


# ===========================================================================
# temporal_field_trend
# ===========================================================================


class TestTemporalFieldTrend:
    def test_empty_cronology_returns_empty(self):
        obj = _make_obj("o1")
        trend = temporal_field_trend(obj, "traffico")
        assert trend == []

    def test_extracts_values_in_window(self):
        obj = _make_obj("o1")
        now = datetime.now(UTC)
        obj.cronologia.append(Stato(campi={"traffico": 10.0}, t=now - timedelta(minutes=30)))
        obj.cronologia.append(Stato(campi={"traffico": 20.0}, t=now - timedelta(minutes=10)))
        trend = temporal_field_trend(obj, "traffico", hours=1.0)
        assert len(trend) == 2
        assert trend[0][1] == 10.0
        assert trend[1][1] == 20.0

    def test_excludes_old_values(self):
        obj = _make_obj("o1")
        now = datetime.now(UTC)
        obj.cronologia.append(Stato(campi={"traffico": 10.0}, t=now - timedelta(hours=3)))
        obj.cronologia.append(Stato(campi={"traffico": 20.0}, t=now - timedelta(minutes=10)))
        trend = temporal_field_trend(obj, "traffico", hours=1.0)
        assert len(trend) == 1
        assert trend[0][1] == 20.0

    def test_ignores_non_numeric_fields(self):
        obj = _make_obj("o1")
        now = datetime.now(UTC)
        obj.cronologia.append(Stato(campi={"traffico": 10.0}, t=now))
        obj.cronologia.append(Stato(campi={"traffico": "sconosciuto"}, t=now))
        trend = temporal_field_trend(obj, "traffico", hours=1.0)
        assert len(trend) == 1


# ===========================================================================
# latest_state_by_object
# ===========================================================================


class TestLatestStateByObject:
    def test_empty_objects(self):
        assert latest_state_by_object([]) == {}

    def test_latest_from_cronologia(self):
        obj = _make_obj("o1")
        now = datetime.now(UTC)
        obj.cronologia.append(Stato(campi={"traffico": 10.0}, t=now - timedelta(minutes=10)))
        obj.cronologia.append(Stato(campi={"traffico": 20.0}, t=now))
        out = latest_state_by_object([obj])
        assert out["o1"]["traffico"] == 20.0

    def test_fallback_to_proprieta(self):
        obj = _make_obj("o1")
        obj.proprieta["traffico"] = 42.0
        out = latest_state_by_object([obj])
        assert out["o1"]["traffico"] == 42.0


# ===========================================================================
# h3_grid_aggregation
# ===========================================================================


class TestH3GridAggregation:
    def test_returns_dict_with_h3(self):
        pytest.importorskip("h3")
        store = _build_world(5)
        grid = h3_grid_aggregation(store.all(), resolution=9)
        assert isinstance(grid, dict)
        assert len(grid) >= 1
        assert len(grid) >= 1


# ===========================================================================
# objects_in_timerange
# ===========================================================================


class TestObjectsInTimerange:
    def test_empty_objects(self):
        assert objects_in_timerange([]) == []

    def test_no_timerange_returns_all(self):
        store = _build_world(5)
        result = objects_in_timerange(list(store.all()))
        assert len(result) == 5

    def test_filters_by_start_time(self):
        obj = _make_obj("o1")
        now = datetime.now(UTC)
        obj.cronologia.append(Stato(campi={"x": 1}, t=now - timedelta(hours=3)))
        result = objects_in_timerange(
            [obj], start=now - timedelta(hours=1), end=now + timedelta(hours=1)
        )
        assert len(result) == 0

    def test_includes_objects_with_no_stati(self):
        obj = _make_obj("o_nostate")
        result = objects_in_timerange([obj])
        assert len(result) == 1
