"""Tests for aethermap.data (Fase 2 storage layer)."""
from __future__ import annotations

import json
from datetime import UTC

import pytest

from aethermap.ai.models import Oggetto, Posizione
from aethermap.data.store import SpatialStore, WorldStore

# ===========================================================================
# Helpers
# ===========================================================================


def _make_obj(oid: str, lat: float = 45.0, lon: float = 9.0, alt: float = 0.0) -> Oggetto:
    return Oggetto(
        id=oid,
        tipo="strada",
        posizione=Posizione.from_latlon(lat, lon, alt),
    )


# ===========================================================================
# SpatialStore
# ===========================================================================


class TestSpatialStoreAddGetRemove:
    def test_add_and_get(self):
        s = SpatialStore()
        obj = _make_obj("o1")
        s.add(obj)
        assert s.get("o1") is obj

    def test_get_missing_returns_none(self):
        s = SpatialStore()
        assert s.get("nope") is None

    def test_remove_returns_true(self):
        s = SpatialStore()
        s.add(_make_obj("o1"))
        assert s.remove("o1") is True

    def test_remove_missing_returns_false(self):
        s = SpatialStore()
        assert s.remove("nope") is False

    def test_len(self):
        s = SpatialStore()
        s.add(_make_obj("o1"))
        s.add(_make_obj("o2"))
        assert len(s) == 2

    def test_all_returns_iterable(self):
        s = SpatialStore()
        s.add(_make_obj("o1"))
        s.add(_make_obj("o2"))
        ids = {o.id for o in s.all()}
        assert ids == {"o1", "o2"}

    def test_ids_returns_iterable(self):
        s = SpatialStore()
        s.add(_make_obj("o1"))
        s.add(_make_obj("o2"))
        assert set(s.ids()) == {"o1", "o2"}


class TestSpatialStoreS2Index:
    def test_query_s2_returns_object(self):
        s = SpatialStore()
        obj = _make_obj("o1", 45.0, 9.0)
        s.add(obj)
        s2 = obj.posizione.s2
        assert s2 is not None
        assert ":" not in s2
        result = s.query_s2(s2)
        assert any(r.id == "o1" for r in result)

    def test_query_s2_empty_store(self):
        s = SpatialStore()
        assert s.query_s2("4:0:123:456") == []

    def test_query_s2_missing_prefix(self):
        s = SpatialStore()
        s.add(_make_obj("o1", 45.0, 9.0))
        result = s.query_s2("0:0:0:0")
        assert result == []

    def test_query_s2_prefix_matches_real_token(self):
        pytest.importorskip("s2sphere")
        s = SpatialStore()
        obj = _make_obj("o1", 45.0, 9.0)
        s.add(obj)
        s2 = obj.posizione.s2
        assert s2 is not None
        prefix = s2[:8]
        result = s.query_s2(prefix)
        assert any(r.id == "o1" for r in result)

    def test_query_h3_returns_object(self):
        s = SpatialStore()
        obj = _make_obj("o1", 45.0, 9.0)
        s.add(obj)
        h3 = obj.posizione.h3
        assert h3 is not None
        result = s.query_h3(h3)
        assert any(r.id == "o1" for r in result)

    def test_query_h3_prefix_matches(self):
        s = SpatialStore()
        obj = _make_obj("o1", 45.0, 9.0)
        s.add(obj)
        h3 = obj.posizione.h3
        assert h3 is not None
        prefix = h3[:9]
        result = s.query_h3(prefix)
        assert any(r.id == "o1" for r in result)

    def test_query_h3_empty_store(self):
        s = SpatialStore()
        assert s.query_h3("8a1fb0bffffff") == []


class TestSpatialStoreRadiusQuery:
    def test_query_radius_finds_nearby(self):
        s = SpatialStore()
        s.add(_make_obj("o1", 45.0, 9.0))
        s.add(_make_obj("o2", 45.001, 9.001))
        s.add(_make_obj("o3", 46.0, 10.0))
        result = s.query_radius(45.0, 9.0, 500.0)
        ids = {r.id for r in result}
        assert "o1" in ids
        assert "o2" in ids
        assert "o3" not in ids

    def test_query_radius_empty_store(self):
        s = SpatialStore()
        assert s.query_radius(45.0, 9.0, 1000.0) == []


class TestSpatialStoreTrim:
    def test_trim_removes_old_stati(self):
        s = SpatialStore()
        obj = _make_obj("o1")
        obj.stale_after_s = 0.1
        from datetime import datetime, timedelta
        old_ts = datetime.now(UTC) - timedelta(seconds=30)
        from aethermap.ai.models import Stato
        obj.cronologia.append(Stato(campi={"x": 1}, confidence=0.5, t=old_ts))
        obj.cronologia.append(Stato(campi={"x": 2}, confidence=0.5))
        s.add(obj)
        import time
        time.sleep(0.15)
        s.trim_stale()
        assert len(obj.cronologia) <= 1

    def test_no_trim_when_stale_after_none(self):
        s = SpatialStore()
        obj = _make_obj("o1")
        obj.stale_after_s = None
        from datetime import datetime, timedelta

        from aethermap.ai.models import Stato
        old_ts = datetime.now(UTC) - timedelta(days=365)
        obj.cronologia.append(Stato(campi={"x": 1}, confidence=0.5, t=old_ts))
        s.add(obj)
        s.trim_stale()
        assert len(obj.cronologia) == 1


# ===========================================================================
# WorldStore
# ===========================================================================


class TestWorldStore:
    def test_add_and_get(self):
        w = WorldStore()
        obj = _make_obj("o1")
        w.add(obj)
        assert w.get("o1") is obj

    def test_remove(self):
        w = WorldStore()
        w.add(_make_obj("o1"))
        assert w.remove("o1") is True
        assert w.get("o1") is None

    def test_to_json(self):
        w = WorldStore()
        w.add(_make_obj("o1"))
        out = w.to_json()
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["id"] == "o1"

    def test_save_and_load_geojson(self, tmp_path):
        w = WorldStore()
        w.add(_make_obj("o1", 45.0, 9.0))
        path = tmp_path / "test.geojson"
        w.save_geojson(path)
        assert path.exists()

        w2 = WorldStore()
        imported = w2.load_geojson(path)
        assert imported == 1
        assert w2.get("o1") is not None
        assert w2.get("o1").tipo == "strada"

    def test_save_and_load_geojson_preserves_s2_h3(self, tmp_path):
        w = WorldStore()
        obj = _make_obj("o1", 45.0, 9.0)
        s2 = obj.posizione.s2
        h3 = obj.posizione.h3
        w.add(obj)
        path = tmp_path / "spatial.geojson"
        w.save_geojson(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        props = raw["features"][0]["properties"]
        assert props.get("s2") == s2
        assert props.get("h3") == h3

        w2 = WorldStore()
        imported = w2.load_geojson(path)
        assert imported == 1
        loaded = w2.get("o1")
        assert loaded is not None
        assert loaded.posizione.s2 == s2
        assert loaded.posizione.h3 == h3

    def test_save_and_load_line_geojson(self, tmp_path):
        w = WorldStore()
        pts = [
            {"lat": 45.0, "lon": 9.0, "ele": 100.0},
            {"lat": 45.001, "lon": 9.001, "ele": 110.0},
        ]
        from aethermap.twin.objects import make_strada
        strada = make_strada("s1", 45.0, 9.0, pts)
        w.add(strada)
        path = tmp_path / "line.geojson"
        w.save_geojson(path)
        raw = path.read_text(encoding="utf-8")
        fc = json.loads(raw)
        assert fc["features"][0]["geometry"]["type"] == "LineString"
        assert len(fc["features"][0]["geometry"]["coordinates"]) == 2

    def test_load_invalid_geojson_skips(self, tmp_path):
        path = tmp_path / "bad.geojson"
        path.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
        w = WorldStore()
        imported = w.load_geojson(path)
        assert imported == 0

    def test_save_parquet_requires_duckdb(self, tmp_path):
        w = WorldStore()
        w.add(_make_obj("o1"))
        path = tmp_path / "test.parquet"
        try:
            w.save_parquet(path)
        except RuntimeError as exc:
            assert "duckdb" in str(exc)
            return
        assert path.exists()

    def test_load_parquet_roundtrip(self, tmp_path):
        pytest.importorskip("duckdb")
        w = WorldStore()
        w.add(_make_obj("o1", 45.0, 9.0, alt=120.0))
        path = tmp_path / "round.parquet"
        w.save_parquet(path)
        w2 = WorldStore()
        imported = w2.load_parquet(path)
        assert imported == 1
        obj = w2.get("o1")
        assert obj is not None
        assert obj.posizione.lat == pytest.approx(45.0)
        assert obj.posizione.alt == pytest.approx(120.0)

    def test_query_s2_via_worldstore(self):
        w = WorldStore()
        obj = _make_obj("o1", 45.0, 9.0)
        w.add(obj)
        s2 = obj.posizione.s2
        assert s2 is not None
        result = w.query_s2(s2)
        assert any(r.id == "o1" for r in result)

    def test_query_radius_via_worldstore(self):
        w = WorldStore()
        w.add(_make_obj("o1", 45.0, 9.0))
        w.add(_make_obj("o2", 45.001, 9.001))
        result = w.query_radius(45.0, 9.0, 500.0)
        ids = {r.id for r in result}
        assert "o1" in ids
        assert "o2" in ids
