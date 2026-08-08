"""Lightweight tests for AetherMap API routes using a minimal FastAPI app."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bike_analyzer.backend.api.aethermap_routes import router as aethermap_router
from aethermap.data.db import AetherMapDB


@pytest.fixture(scope="module")
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def app(db_path):
    os.environ["AETHERMAP_DB_PATH"] = db_path
    app = FastAPI()
    app.include_router(aethermap_router, prefix="/api/v1/aethermap", tags=["aethermap"])
    yield app
    del os.environ["AETHERMAP_DB_PATH"]


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_aethermap_db(db_path):
    from bike_analyzer.backend.api.aethermap_routes import _DB_CACHE
    for db in _DB_CACHE.values():
        try:
            db.close()
        except Exception:
            pass
    _DB_CACHE.clear()
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except OSError:
            pass
    yield


class TestAetherMapHealth:
    def test_health(self, client):
        resp = client.get("/api/v1/aethermap/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "service": "aethermap"}


class TestAetherMapCRUD:
    def test_create_and_get_object(self, client):
        payload = {
            "id": "poi-1",
            "tipo": "poi",
            "lat": 45.0,
            "lon": 9.0,
            "proprieta": {"nome": "Test POI", "categoria": "fontana"},
        }
        resp = client.post("/api/v1/aethermap/objects", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == "poi-1"
        assert data["tipo"] == "poi"
        assert data["lat"] == 45.0
        assert data["proprieta"]["nome"] == "Test POI"

        resp = client.get("/api/v1/aethermap/objects/poi-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "poi-1"

    def test_create_strada(self, client):
        payload = {
            "id": "strada-1",
            "tipo": "strada",
            "lat": 45.0,
            "lon": 9.0,
            "geometria": {"tipo": "linea", "dati": {"punti": [{"lat": 45.0, "lon": 9.0, "ele": 100.0}]}},
            "proprieta": {"asfalto": "buono"},
        }
        resp = client.post("/api/v1/aethermap/objects", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["geometria"]["tipo"] == "linea"

    def test_update_object(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        resp = client.put("/api/v1/aethermap/objects/o1", json={"proprieta": {"nome": "Updated"}})
        assert resp.status_code == 200
        assert resp.json()["proprieta"]["nome"] == "Updated"

    def test_delete_object(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        resp = client.delete("/api/v1/aethermap/objects/o1")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}
        resp = client.get("/api/v1/aethermap/objects/o1")
        assert resp.status_code == 404

    def test_list_objects(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        client.post("/api/v1/aethermap/objects", json={"id": "o2", "tipo": "strada", "lat": 46.0, "lon": 10.0})
        resp = client.get("/api/v1/aethermap/objects")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_objects_filter_by_tipo(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        client.post("/api/v1/aethermap/objects", json={"id": "o2", "tipo": "strada", "lat": 46.0, "lon": 10.0})
        resp = client.get("/api/v1/aethermap/objects?tipo=poi")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["tipo"] == "poi"


class TestAetherMapSpatialQueries:
    def test_nearby(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        client.post("/api/v1/aethermap/objects", json={"id": "o2", "tipo": "poi", "lat": 45.001, "lon": 9.001})
        client.post("/api/v1/aethermap/objects", json={"id": "o3", "tipo": "poi", "lat": 46.0, "lon": 10.0})
        resp = client.get("/api/v1/aethermap/objects/nearby?lat=45.0&lon=9.0&radius_km=5")
        assert resp.status_code == 200
        ids = {o["id"] for o in resp.json()}
        assert "o1" in ids
        assert "o2" in ids
        assert "o3" not in ids

    def test_bounds(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        client.post("/api/v1/aethermap/objects", json={"id": "o2", "tipo": "poi", "lat": 46.0, "lon": 10.0})
        resp = client.get("/api/v1/aethermap/objects/bounds?lat_min=44.9&lat_max=45.1&lon_min=8.9&lon_max=9.1")
        assert resp.status_code == 200
        ids = {o["id"] for o in resp.json()}
        assert "o1" in ids
        assert "o2" not in ids

    def test_within(self, client):
        client.post("/api/v1/aethermap/objects", json={"id": "o1", "tipo": "poi", "lat": 45.0, "lon": 9.0})
        client.post("/api/v1/aethermap/objects", json={"id": "o2", "tipo": "poi", "lat": 46.0, "lon": 10.0})
        resp = client.get("/api/v1/aethermap/objects/within?lat=45.0&lon=9.0&delta_km=5")
        assert resp.status_code == 200
        ids = {o["id"] for o in resp.json()}
        assert "o1" in ids
        assert "o2" not in ids

    def test_bounds_invalid(self, client):
        resp = client.get("/api/v1/aethermap/objects/bounds?lat_min=10&lat_max=5&lon_min=8&lon_max=9")
        assert resp.status_code == 400
