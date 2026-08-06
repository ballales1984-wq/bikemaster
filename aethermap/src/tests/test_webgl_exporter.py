"""Tests for aethermap.render.webgl_exporter (Phase 4 rendering)."""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import numpy as np

from aethermap.render.webgl_exporter import (
    _build_heightfield,
    _entity_color,
    _entity_to_gl,
    _terrain_mesh_from_hf,
    export_world,
)
from aethermap.twin.objects import make_albero, make_montagna, make_strada
from aethermap.twin.world import DigitalTwin, Environment


class TestBuildHeightfield:
    def test_returns_nx_n_array(self):
        hf = _build_heightfield(n=16, base_alt=0.0, height_scale=0.04)
        assert hf.shape == (16, 16)

    def test_values_in_expected_range(self):
        hf = _build_heightfield(n=16, base_alt=1.0, height_scale=0.5)
        assert float(hf.min()) >= 1.0
        assert float(hf.max()) <= 1.0 + 0.5

    def test_base_alt_shifts_output(self):
        hf0 = _build_heightfield(n=8, base_alt=0.0, height_scale=0.0)
        hf1 = _build_heightfield(n=8, base_alt=10.0, height_scale=0.0)
        assert math.isclose(float(hf0.min()), 0.0, abs_tol=1e-9)
        assert math.isclose(float(hf1.min()), 10.0, abs_tol=1e-9)


class TestTerrainMeshFromHf:
    def test_returns_expected_keys(self):
        hf = np.zeros((6, 8, 8), dtype=np.float32)
        mesh = _terrain_mesh_from_hf(hf.flatten(), 8)
        for k in ("positions", "normals", "indices", "grid_size", "faces"):
            assert k in mesh

    def test_faces_count(self):
        hf = np.zeros((6, 8, 8), dtype=np.float32)
        mesh = _terrain_mesh_from_hf(hf.flatten(), 8)
        assert mesh["faces"] == 6
        assert mesh["grid_size"] == 10  # 8 + skirt*2

    def test_positions_normals_indices_lengths(self):
        hf = np.zeros((6, 8, 8), dtype=np.float32)
        mesh = _terrain_mesh_from_hf(hf.flatten(), 8)
        n_verts = 6 * mesh["grid_size"] * mesh["grid_size"]
        assert len(mesh["positions"]) == n_verts
        assert len(mesh["normals"]) == n_verts
        assert len(mesh["indices"]) == 6 * (mesh["grid_size"] - 1) * (mesh["grid_size"] - 1) * 6


class TestEntityColor:
    def test_known_types(self):
        assert _entity_color("strada") == [0.95, 0.78, 0.22]
        assert _entity_color("albero") == [0.28, 0.92, 0.42]
        assert _entity_color("montagna") == [0.92, 0.32, 0.28]

    def test_unknown_type_default(self):
        assert _entity_color("sconosciuto") == [0.8, 0.8, 0.8]


class TestEntityToGl:
    def test_strada_export(self):
        strada = make_strada("s1", 45.0, 9.0, [
            {"lat": 45.0, "lon": 9.0, "ele": 100.0},
            {"lat": 45.001, "lon": 9.001, "ele": 105.0},
        ])
        entry = _entity_to_gl(strada)
        assert entry["id"] == "s1"
        assert entry["tipo"] == "strada"
        assert entry["kind"] == "line"
        assert len(entry["points"]) == 2
        assert all(len(p) == 3 for p in entry["points"])

    def test_albero_export(self):
        albero = make_albero("a1", 45.005, 9.01, "quercia", 8.5)
        albero.posizione.alt = 8.5
        entry = _entity_to_gl(albero)
        assert entry["id"] == "a1"
        assert entry["tipo"] == "albero"
        assert entry["kind"] == "point"
        assert entry["height_m"] == 8.5
        assert len(entry["position"]) == 3

    def test_montagna_export(self):
        montagna = make_montagna("m1", 45.015, 9.03, 1800.0, ["nord", "sud"])
        entry = _entity_to_gl(montagna)
        assert entry["id"] == "m1"
        assert entry["tipo"] == "montagna"
        assert entry["kind"] == "point"
        assert entry["radius"] > 0
        assert "svo_stats" in entry["props"]


class TestExportWorld:
    def test_writes_valid_json(self):
        twin = DigitalTwin()
        twin.add(make_strada("s1", 45.0, 9.0, [
            {"lat": 45.0, "lon": 9.0, "ele": 100.0},
        ]))
        twin.add(make_albero("a1", 45.005, 9.01, "pino", 5.0))
        env = Environment(temp_c=15.0, solar_elev_deg=30.0, ora="12:00")
        twin.step(env)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name

        export_world(twin, path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))

        assert data["version"] == "aethermap-webgl-1.0"
        assert "terrain" in data
        assert "entities" in data
        assert "relations" in data
        assert "camera" in data
        assert "earth_r" in data
        assert len(data["entities"]) == 2
