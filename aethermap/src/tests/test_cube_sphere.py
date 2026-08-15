"""Tests for aethermap.core.cube_sphere (Phase 1)."""
from __future__ import annotations

import math

import pytest

from aethermap.core.cube_sphere import (
    CubeSphereCell,
    cell_area,
    cell_center_geodetic,
    cell_direction,
    cell_ground_resolution,
    cell_neighbors,
    direction_to_face_uv,
    face_at_level,
    face_uv_to_direction,
    latlon_to_cell,
    level_for_cell_count,
    level_for_resolution,
    root_cells,
    subdivide_to_level,
)


class TestFaceDefinitions:
    def test_six_root_cells(self):
        roots = root_cells()
        assert len(roots) == 6
        faces = {c.face for c in roots}
        assert faces == {0, 1, 2, 3, 4, 5}

    def test_root_cells_level_zero(self):
        for cell in root_cells():
            assert cell.level == 0
            assert cell.u_min == -1.0
            assert cell.u_max == 1.0
            assert cell.v_min == -1.0
            assert cell.v_max == 1.0

    def test_face_at_level(self):
        cell = face_at_level(3, 2)
        assert cell.face == 3
        assert cell.level == 2

    def test_invalid_face_raises(self):
        with pytest.raises(ValueError):
            CubeSphereCell(face=6, level=0, u_min=-1, u_max=1, v_min=-1, v_max=1)

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            CubeSphereCell(face=0, level=-1, u_min=-1, u_max=1, v_min=-1, v_max=1)


class TestDirectionFaceMapping:
    def test_positive_x_face(self):
        face, u, v = direction_to_face_uv(1.0, 0.0, 0.0)
        assert face == 0
        assert math.isclose(u, 0.0)
        assert math.isclose(v, 0.0)

    def test_negative_x_face(self):
        face, u, v = direction_to_face_uv(-1.0, 0.0, 0.0)
        assert face == 1

    def test_positive_y_face(self):
        face, u, v = direction_to_face_uv(0.0, 1.0, 0.0)
        assert face == 2

    def test_negative_z_face(self):
        face, u, v = direction_to_face_uv(0.0, 0.0, -1.0)
        assert face == 5

    def test_round_trip_direction(self):
        import math
        for dx, dy, dz in [
            (0.5, 0.3, 0.8),
            (0.1, -0.9, 0.4),
            (-0.7, 0.2, -0.6),
        ]:
            norm = math.sqrt(dx**2 + dy**2 + dz**2)
            face, u, v = direction_to_face_uv(dx / norm, dy / norm, dz / norm)
            rx, ry, rz = face_uv_to_direction(face, u, v)
            rnorm = math.sqrt(rx**2 + ry**2 + rz**2)
            assert math.isclose(rx / rnorm, dx / norm, abs_tol=1e-10)
            assert math.isclose(ry / rnorm, dy / norm, abs_tol=1e-10)
            assert math.isclose(rz / rnorm, dz / norm, abs_tol=1e-10)


class TestSubdivision:
    def test_subdivide_creates_four_children(self):
        root = face_at_level(0, 0)
        children = root.subdivide()
        assert len(children) == 4
        for child in children:
            assert child.face == 0
            assert child.level == 1

    def test_subdivide_children_cover_parent(self):
        root = face_at_level(0, 0)
        children = root.subdivide()
        u_min = min(c.u_min for c in children)
        u_max = max(c.u_max for c in children)
        v_min = min(c.v_min for c in children)
        v_max = max(c.v_max for c in children)
        assert math.isclose(u_min, -1.0, abs_tol=1e-10)
        assert math.isclose(u_max, 1.0, abs_tol=1e-10)
        assert math.isclose(v_min, -1.0, abs_tol=1e-10)
        assert math.isclose(v_max, 1.0, abs_tol=1e-10)

    def test_subdivide_to_level(self):
        cells = subdivide_to_level(0, 2)
        assert len(cells) == 4**2  # 16 cells at level 2
        for cell in cells:
            assert cell.level == 2
            assert cell.face == 0

    def test_subdivide_max_level(self):
        cell = CubeSphereCell(face=0, level=29, u_min=0, u_max=0.1, v_min=0, v_max=0.1)
        children = cell.subdivide()
        assert len(children) == 4
        assert all(c.level == 30 for c in children)

    def test_subdivide_beyond_max_raises(self):
        cell = CubeSphereCell(face=0, level=30, u_min=0, u_max=0.1, v_min=0, v_max=0.1)
        with pytest.raises(ValueError):
            cell.subdivide()


class TestCellGeometry:
    def test_cell_center_geodetic(self):
        cell = face_at_level(0, 0)
        lat, lon = cell_center_geodetic(cell)
        assert math.isclose(lat, 0.0, abs_tol=1e-6)
        assert math.isclose(lon, 0.0, abs_tol=1e-6)

    def test_cell_direction_unit_length(self):
        for face in range(6):
            cell = face_at_level(face, 0)
            dx, dy, dz = cell_direction(cell)
            assert math.isclose(math.sqrt(dx**2 + dy**2 + dz**2), 1.0, abs_tol=1e-10)

    def test_cell_area_positive(self):
        cell = face_at_level(0, 0)
        area = cell_area(cell)
        assert area > 0.0

    def test_cell_area_decreases_with_level(self):
        cells_l0 = subdivide_to_level(0, 0)
        cells_l1 = subdivide_to_level(0, 1)
        area_l0 = cell_area(cells_l0[0])
        area_l1 = cell_area(cells_l1[0])
        assert area_l1 < area_l0

    def test_cell_ground_resolution_decreases_with_level(self):
        res_l0 = cell_ground_resolution(face_at_level(0, 0))
        res_l1 = cell_ground_resolution(face_at_level(0, 1))
        assert res_l1 < res_l0

    def test_total_surface_area_six_faces(self):
        total = sum(cell_area(face_at_level(f, 0)) for f in range(6))
        earth_area = 4.0 * math.pi * 6_371_000.0**2
        assert math.isclose(total, earth_area, rel_tol=0.01)


class TestCellNeighbors:
    def test_neighbors_count(self):
        cell = CubeSphereCell(face=0, level=1, u_min=0, u_max=0.5, v_min=0, v_max=0.5)
        neighbors = cell_neighbors(cell)
        assert len(neighbors) == 4

    def test_neighbors_do_not_include_self(self):
        cell = CubeSphereCell(face=0, level=1, u_min=0, u_max=0.5, v_min=0, v_max=0.5)
        neighbors = cell_neighbors(cell)
        for n in neighbors:
            assert not (n.face == cell.face and n.u_min == cell.u_min and n.u_max == cell.u_max
                        and n.v_min == cell.v_min and n.v_max == cell.v_max)


class TestContainment:
    def test_contains_center_point(self):
        cell = face_at_level(2, 0)
        lat, lon = cell_center_geodetic(cell)
        assert cell.contains(lat, lon)

    def test_contains_false_for_opposite_face(self):
        cell = face_at_level(0, 0)
        # Point on face 5 (opposite of 0) should not be in face 0
        opposite = face_at_level(5, 0)
        lat, lon = cell_center_geodetic(opposite)
        assert not cell.contains(lat, lon)


class TestLOD:
    def test_level_for_resolution(self):
        level = level_for_resolution(1000.0)  # 1 km resolution
        assert isinstance(level, int)
        assert level >= 0

    def test_level_for_cell_count(self):
        level = level_for_cell_count(1024)
        assert (2**level) ** 2 >= 1024

    def test_latlon_to_cell(self):
        cell = latlon_to_cell(45.0, 9.0, level=2)
        assert cell.level == 2
        assert cell.face in range(6)


class TestCellId:
    def test_cell_id_format(self):
        cell = CubeSphereCell(face=2, level=4, u_min=-0.5, u_max=0.5, v_min=-0.3, v_max=0.3)
        cid = cell.cell_id()
        parts = cid.split(":")
        assert len(parts) == 6
        assert parts[0] == "2"
        assert parts[1] == "4"

    def test_cell_id_unique_per_cell(self):
        cells = subdivide_to_level(0, 3)
        ids = [c.cell_id() for c in cells]
        assert len(ids) == len(set(ids))
