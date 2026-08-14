"""Tests for AetherMap API endpoints (Fase 4 backend integration)."""
from __future__ import annotations

import math

import pytest

from bike_analyzer.backend.db import database as db_mod


class TestAetherMapWorld:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/aethermap/world")
        assert resp.status_code == 200

    def test_returns_expected_keys(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        for k in ("version", "terrain", "entities", "relations", "camera", "earth_r"):
            assert k in data

    def test_terrain_has_faces_and_positions(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        assert data["terrain"]["faces"] == 6
        assert len(data["terrain"]["positions"]) > 0
        assert len(data["terrain"]["normals"]) == len(data["terrain"]["positions"])
        assert len(data["terrain"]["indices"]) > 0

    def test_entities_have_required_fields(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        assert len(data["entities"]) >= 3
        for ent in data["entities"]:
            assert "id" in ent
            assert "tipo" in ent
            assert "kind" in ent
            assert "color" in ent

    def test_relations_match_entities(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        entity_ids = {e["id"] for e in data["entities"]}
        for rel in data["relations"]:
            assert rel["from"] in entity_ids
            assert rel["to"] in entity_ids

    def test_camera_has_yaw_pitch(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        assert "yaw" in data["camera"]
        assert "pitch" in data["camera"]


class TestAetherMapTerrainTile:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=0&resolution=32")
        assert resp.status_code == 200

    def test_validates_face_range(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=-1&resolution=32")
        assert resp.status_code == 422
        resp = client.get("/api/v1/aethermap/terrain-tile?face=6&resolution=32")
        assert resp.status_code == 422

    def test_validates_resolution_range(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=0&resolution=7")
        assert resp.status_code == 422
        resp = client.get("/api/v1/aethermap/terrain-tile?face=0&resolution=257")
        assert resp.status_code == 422

    def test_returns_expected_keys(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=2&resolution=32")
        data = resp.json()
        for k in ("positions", "normals", "indices", "grid_size", "face", "resolution", "source"):
            assert k in data

    def test_face_matches_request(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=3&resolution=16")
        data = resp.json()
        assert data["face"] == 3
        assert data["resolution"] == 16

    def test_positions_count_matches_grid(self, client):
        resp = client.get("/api/v1/aethermap/terrain-tile?face=1&resolution=16")
        data = resp.json()
        n = data["grid_size"]
        assert len(data["positions"]) == n * n
        assert len(data["normals"]) == n * n
        assert len(data["indices"]) == (n - 1) * (n - 1) * 6

    def test_all_faces_produce_output(self, client):
        for face in range(6):
            resp = client.get(
                f"/api/v1/aethermap/terrain-tile?face={face}&resolution=16"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["positions"]) > 0


class TestAetherMapIntegration:
    def test_world_data_is_valid_for_renderer(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        assert data["version"] == "aethermap-webgl-1.0"
        assert isinstance(data["terrain"]["positions"], list)
        assert all(isinstance(p, list) and len(p) == 3 for p in data["terrain"]["positions"])
        assert all(isinstance(p, list) and len(p) == 3 for p in data["terrain"]["normals"])
        assert all(isinstance(e, dict) for e in data["entities"])
        assert all(isinstance(r, dict) for r in data["relations"])

    def test_world_terrain_indices_are_triangles(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        assert len(data["terrain"]["indices"]) % 3 == 0

    def test_world_entity_positions_are_unit_sphere(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        for ent in data["entities"]:
            if ent.get("position"):
                px, py, pz = ent["position"]
                dist = math.sqrt(px * px + py * py + pz * pz)
                assert abs(dist - 1.0) < 0.5, f"{ent['id']} distance={dist}"

    def test_world_relations_reference_existing_entities(self, client):
        resp = client.get("/api/v1/aethermap/world")
        data = resp.json()
        ids = {e["id"] for e in data["entities"]}
        for rel in data["relations"]:
            assert rel["from"] in ids, f"from={rel['from']} missing"
            assert rel["to"] in ids, f"to={rel['to']} missing"


class TestRideTerrainEnrichment:
    @pytest.mark.missing_greenlet
    def test_returns_enriched_gps_points(self, client, monkeypatch):
        from bike_analyzer.backend.api.routes import _s
        monkeypatch.setattr(_s, "terrain_enrichment_enabled", True)

        ride_id = db_mod.save_ride({
            "athlete_id": 0,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0,
            "elevation_gain_m": 200.0,
            "calories": 600.0,
            "gps_points": [
                {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z", "altitude": 200.0},
                {"lat": 45.1, "lon": 7.1, "timestamp": "2024-06-15T10:01:00Z", "altitude": 210.0},
            ],
        })

        resp = client.get(f"/api/v1/rides/{ride_id}/terrain", params={"enabled": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ride_id"] == ride_id
        assert len(data["enriched"]) == 2
        for pt in data["enriched"]:
            assert "slope_pct" in pt
            assert "surface_type" in pt
            assert "shade" in pt
            assert "traffic_level" in pt
            assert "terrain_confidence" in pt

    @pytest.mark.missing_greenlet
    def test_returns_403_when_disabled_and_requested(self, client, monkeypatch):
        from bike_analyzer.backend.api.routes import _s
        monkeypatch.setattr(_s, "terrain_enrichment_enabled", False)

        ride_id = db_mod.save_ride({
            "athlete_id": 0,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0,
            "elevation_gain_m": 200.0,
            "calories": 600.0,
            "gps_points": [
                {"lat": 45.0, "lon": 7.0, "timestamp": "2024-06-15T10:00:00Z", "altitude": 200.0},
            ],
        })

        resp = client.get(f"/api/v1/rides/{ride_id}/terrain", params={"enabled": True})
        assert resp.status_code == 403

    @pytest.mark.missing_greenlet
    def test_returns_404_for_missing_ride(self, client, monkeypatch):
        from bike_analyzer.backend.api.routes import _s
        monkeypatch.setattr(_s, "terrain_enrichment_enabled", True)

        resp = client.get("/api/v1/rides/99999/terrain", params={"enabled": True})
        assert resp.status_code == 404

    @pytest.mark.missing_greenlet
    def test_returns_400_without_gps(self, client, monkeypatch):
        from bike_analyzer.backend.api.routes import _s
        monkeypatch.setattr(_s, "terrain_enrichment_enabled", True)

        ride_id = db_mod.save_ride({
            "athlete_id": 0,
            "date": "2024-06-15T10:00:00Z",
            "distance_km": 25.0,
            "duration_minutes": 60.0,
            "avg_speed_kmh": 25.0,
            "elevation_gain_m": 200.0,
            "calories": 600.0,
        })

        resp = client.get(f"/api/v1/rides/{ride_id}/terrain", params={"enabled": True})
        assert resp.status_code == 400

