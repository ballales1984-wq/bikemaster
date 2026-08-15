"""Tests for aethermap.data.db (SQLite persistence layer)."""
from __future__ import annotations

import pytest

from aethermap.ai.models import Oggetto, Posizione, Stato
from aethermap.data.db import AetherMapDB
from aethermap.data.store import PersistentStore
from aethermap.twin.world import DigitalTwin

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
# AetherMapDB
# ===========================================================================


class TestAetherMapDBCreateClose:
    def test_creates_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = AetherMapDB(db_path)
        db.close()
        assert db_path.exists()

    def test_context_manager(self, tmp_path):
        db_path = tmp_path / "ctx.db"
        with AetherMapDB(db_path) as db:
            assert db.path == db_path
        assert db_path.exists()


class TestAetherMapDBAddGetRemove:
    def test_add_and_get(self, tmp_path):
        db = AetherMapDB(tmp_path / "t1.db")
        obj = _make_obj("o1")
        db.add(obj)
        loaded = db.get("o1")
        assert loaded is not None
        assert loaded.id == "o1"
        assert loaded.tipo == "strada"
        assert loaded.posizione.lat == pytest.approx(45.0)
        assert loaded.posizione.lon == pytest.approx(9.0)
        db.close()

    def test_get_missing_returns_none(self, tmp_path):
        db = AetherMapDB(tmp_path / "t2.db")
        assert db.get("nope") is None
        db.close()

    def test_remove(self, tmp_path):
        db = AetherMapDB(tmp_path / "t3.db")
        db.add(_make_obj("o1"))
        assert db.count() == 1
        result = db.remove("o1")
        assert result is True
        assert db.count() == 0
        assert db.get("o1") is None
        db.close()

    def test_remove_missing(self, tmp_path):
        db = AetherMapDB(tmp_path / "t4.db")
        assert db.remove("nope") is False
        db.close()

    def test_count(self, tmp_path):
        db = AetherMapDB(tmp_path / "t5.db")
        assert db.count() == 0
        db.add(_make_obj("o1"))
        db.add(_make_obj("o2"))
        assert db.count() == 2
        db.close()

    def test_add_replaces_existing(self, tmp_path):
        db = AetherMapDB(tmp_path / "t6.db")
        db.add(_make_obj("o1", 45.0, 9.0))
        db.add(_make_obj("o1", 46.0, 10.0))
        assert db.count() == 1
        obj = db.get("o1")
        assert obj.posizione.lat == pytest.approx(46.0)
        db.close()


class TestAetherMapDBPersistence:
    def test_data_survives_reopen(self, tmp_path):
        db_path = tmp_path / "persist.db"
        db1 = AetherMapDB(db_path)
        db1.add(_make_obj("o1", 45.0, 9.0, alt=120.0))
        db1.close()

        db2 = AetherMapDB(db_path)
        obj = db2.get("o1")
        assert obj is not None
        assert obj.id == "o1"
        assert obj.posizione.lat == pytest.approx(45.0)
        assert obj.posizione.lon == pytest.approx(9.0)
        assert obj.posizione.alt == pytest.approx(120.0)
        db2.close()

    def test_multiple_objects_persist(self, tmp_path):
        db_path = tmp_path / "multi.db"
        with AetherMapDB(db_path) as db:
            db.add(_make_obj("o1", 45.0, 9.0))
            db.add(_make_obj("o2", 46.0, 10.0))
            db.add(_make_obj("o3", 47.0, 11.0))

        with AetherMapDB(db_path) as db:
            assert db.count() == 3
            assert db.get("o1") is not None
            assert db.get("o2") is not None
            assert db.get("o3") is not None

    def test_state_history_persists(self, tmp_path):
        db_path = tmp_path / "states.db"
        obj = _make_obj("o1")
        obj.cronologia.append(Stato(campi={"temp": 20.0}, confidence=0.9))
        with AetherMapDB(db_path) as db:
            db.add(obj)

        with AetherMapDB(db_path) as db:
            loaded = db.get("o1")
            assert loaded is not None
            assert len(loaded.cronologia) == 1
            assert loaded.cronologia[0].campi["temp"] == pytest.approx(20.0)
            assert loaded.cronologia[0].confidence == pytest.approx(0.9)


class TestAetherMapDBByTipo:
    def test_get_by_tipo(self, tmp_path):
        db = AetherMapDB(tmp_path / "tipo.db")
        db.add(_make_obj("o1", 45.0, 9.0))
        db.add(_make_obj("o2", 46.0, 10.0))
        from aethermap.twin.objects import make_albero
        albero = make_albero("a1", 45.5, 9.5, "quercia", 5.0)
        db.add(albero)
        strade = db.get_by_tipo("strada")
        assert len(strade) == 2
        alberi = db.get_by_tipo("albero")
        assert len(alberi) == 1
        db.close()


class TestAetherMapDBQueryRadius:
    def test_query_radius(self, tmp_path):
        db = AetherMapDB(tmp_path / "radius.db")
        db.add(_make_obj("o1", 45.0, 9.0))
        db.add(_make_obj("o2", 45.001, 9.001))
        db.add(_make_obj("o3", 46.0, 10.0))
        results = db.query_radius(45.0, 9.0, 500.0)
        ids = {r.id for r in results}
        assert "o1" in ids
        assert "o2" in ids
        assert "o3" not in ids
        db.close()


class TestAetherMapDBQueryBounds:
    def test_query_bounds(self, tmp_path):
        db = AetherMapDB(tmp_path / "bounds.db")
        db.add(_make_obj("o1", 45.0, 9.0))
        db.add(_make_obj("o2", 45.001, 9.001))
        db.add(_make_obj("o3", 46.0, 10.0))
        results = db.query_bounds(44.9, 45.1, 8.9, 9.1)
        ids = {r.id for r in results}
        assert "o1" in ids
        assert "o2" in ids
        assert "o3" not in ids
        db.close()

    def test_query_bounds_empty(self, tmp_path):
        db = AetherMapDB(tmp_path / "bounds_empty.db")
        results = db.query_bounds(44.9, 45.1, 8.9, 9.1)
        assert results == []
        db.close()


# ===========================================================================
# PersistentStore
# ===========================================================================


class TestPersistentStore:
    def test_creates_db_on_init(self, tmp_path):
        db_path = tmp_path / "store.db"
        assert not db_path.exists()
        ps = PersistentStore(db_path=db_path)
        assert db_path.exists()
        ps.close()

    def test_loads_existing_data(self, tmp_path):
        db_path = tmp_path / "load.db"
        with AetherMapDB(db_path) as db:
            db.add(_make_obj("o1", 45.0, 9.0))
            db.add(_make_obj("o2", 46.0, 10.0))

        ps = PersistentStore(db_path=db_path)
        assert ps.count() == 2
        assert ps.get("o1") is not None
        assert ps.get("o2") is not None
        ps.close()

    def test_add_persists(self, tmp_path):
        db_path = tmp_path / "add_persist.db"
        ps = PersistentStore(db_path=db_path)
        ps.add(_make_obj("o1", 45.0, 9.0))
        ps.close()

        ps2 = PersistentStore(db_path=db_path)
        assert ps2.count() == 1
        assert ps2.get("o1") is not None
        ps2.close()

    def test_remove_syncs(self, tmp_path):
        db_path = tmp_path / "remove.db"
        ps = PersistentStore(db_path=db_path)
        ps.add(_make_obj("o1"))
        assert ps.remove("o1") is True
        ps.close()

        ps2 = PersistentStore(db_path=db_path)
        assert ps2.count() == 0
        ps2.close()

    def test_db_count_matches_store(self, tmp_path):
        ps = PersistentStore(db_path=tmp_path / "count.db")
        ps.add(_make_obj("o1"))
        ps.add(_make_obj("o2"))
        assert ps.count() == ps.db_count() == 2
        ps.close()


# ===========================================================================
# DigitalTwin with persistence
# ===========================================================================


class TestDigitalTwinPersistent:
    def test_default_not_persistent(self):
        dt = DigitalTwin()
        assert dt._persistent_store is None
        from aethermap.twin.objects import make_strada
        dt.add(make_strada("s1", 45.0, 9.0, []))
        assert len(dt.store.objects) == 1
        dt2 = DigitalTwin()
        assert len(dt2.store.objects) == 0

    def test_persistent_loads_from_db(self, tmp_path):
        db_path = tmp_path / "dt_persist.db"
        with AetherMapDB(db_path) as db:
            db.add(_make_obj("o1", 45.0, 9.0))

        dt = DigitalTwin(persistent=True, db_path=db_path)
        assert len(dt.store.objects) == 1
        assert dt.store.get("o1") is not None

    def test_persistent_add_survives_reopen(self, tmp_path):
        db_path = tmp_path / "dt_add.db"
        dt = DigitalTwin(persistent=True, db_path=db_path)
        from aethermap.twin.objects import make_albero, make_strada
        dt.add(make_strada("s1", 45.0, 9.0, []))
        dt.add(make_albero("a1", 45.5, 9.5, "pino", 8.0))

        dt2 = DigitalTwin(persistent=True, db_path=db_path)
        assert len(dt2.store.objects) == 2
        assert dt2.store.get("s1") is not None
        assert dt2.store.get("a1") is not None

    def test_persistent_save_json_still_works(self, tmp_path):
        db_path = tmp_path / "dt_json.db"
        dt = DigitalTwin(persistent=True, db_path=db_path)
        from aethermap.twin.objects import make_strada
        dt.add(make_strada("s1", 45.0, 9.0, []))
        out_path = tmp_path / "export.json"
        dt.save_json(out_path)
        assert out_path.exists()
        import json
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["id"] == "s1"
