"""Regression tests for the camera projection (Fase 1 §3.1 / §6.2).

These guard against the transposed perspective matrix that once collapsed the
whole globe to a single centre dot: the depth (z) and w rows must be in the
standard right-handed OpenGL glPerspective form.
"""

import math

import numpy as np

from aethermap.render.camera import Camera
from aethermap.render.projection import cube_sphere_mesh, project_ecef


def test_projection_matrix_has_standard_glperspective_rows():
    cam = Camera()
    m = cam.projection_matrix()

    nf = 1.0 / (cam.near - cam.far)
    # row2[3] must hold 2*far*near*nf, row3[2] must be -1.0
    assert m[2][3] == 2.0 * cam.far * cam.near * nf
    assert m[3][2] == -1.0


def test_globe_projection_spans_ndc_not_a_dot():
    cam = Camera()
    xs, ys = [], []
    for a, b in cube_sphere_mesh(8):
        for p in (a, b):
            r = project_ecef(p, cam)
            if r:
                xs.append(r[0])
                ys.append(r[1])

    assert max(abs(min(xs)), abs(max(xs))) > 0.1
    assert max(abs(min(ys)), abs(max(ys))) > 0.1


def test_camera_look_at_point_is_screen_centered():
    """The camera origin (the point being looked at) must project to NDC (0,0).

    Regresses the double-shift bug: project_ecef() subtracts the camera origin
    T before applying the MVP, but view_matrix() is a world-space lookAt that
    subtracted the absolute eye position P = T + forward*distance. That double
    translation pushed every vertex ~1.5e7 m off, so the look-at point landed
    around NDC (0.3, -0.23) instead of (0,0) and the whole globe was offset.
    """
    cam = Camera()
    ox, oy, oz = cam.ecef_origin()
    ndc = project_ecef(np.array([ox, oy, oz], dtype=np.float64), cam)
    assert ndc is not None
    assert abs(ndc[0]) < 1e-6
    assert abs(ndc[1]) < 1e-6


def test_back_facing_vertices_are_culled():
    cam = Camera()
    ox, oy, oz = cam.ecef_origin()

    # The camera eye sits at origin + forward*distance; a point further along
    # that direction (beyond the eye) is behind the camera and must be culled.
    cy_, sy_ = math.cos(cam.yaw), math.sin(cam.yaw)
    cp_, sp_ = math.cos(cam.pitch), math.sin(cam.pitch)
    fx, fy, fz = cy_ * cp_, sp_, sy_ * cp_
    eye_behind = np.array(
        [ox + fx * cam.distance * 2.0,
         oy + fy * cam.distance * 2.0,
         oz + fz * cam.distance * 2.0],
        dtype=np.float64,
    )

    assert project_ecef(eye_behind, cam) is None
    # And the surface point the camera looks at must still project fine.
    assert project_ecef(np.array([ox, oy, oz], dtype=np.float64), cam) is not None
