# Fix: globe collapses to a dot — transposed perspective matrix in `camera.py`

## Context
The AetherMap ASCII prototype (`render/demo.py` → `render/ascii.py` → `render/projection.project_ecef`) renders a cube-sphere globe via `Camera.mvp()` (real Earth-metre ECEF + camera-relative subtract, Fase 1 §3.1/§6.2). The globe came out as a single dot at screen centre, with all 600+ mesh points projecting to NDC ≈ (0, 0).

### Root cause (verified, not guessed)
`aethermap/render/camera.py::Camera.projection_matrix()` (lines 81–86) returns a perspective matrix with the **depth (`z`) and `w` rows transposed** relative to a standard right-handed OpenGL perspective matrix:

```python
# BUGGY (current)
[ f/aspect, 0, 0, 0 ]
[ 0, f, 0, 0 ]
[ 0, 0, (far+near)*nf,      -1.0 ]   # row2: should hold 2*far*near*nf here
[ 0, 0, 2*far*near*nf,       0.0 ]   # row3: should be -1.0 here

# CORRECT glPerspective
[ f/aspect, 0, 0, 0 ]
[ 0, f, 0, 0 ]
[ 0, 0, (far+near)*nf, 2*far*near*nf ]
[ 0, 0, -1.0,              0.0       ]
```

With the bug, `w_clip = 2·far·near·nf · z_cam ≈ -2·near·z_cam`. At `near=100` that is an extra ×~200 shrink, so `NDC = clip.xy / w` collapses to ≈0.005 for every vertex → globe renders as one centre dot.

Empirically confirmed by running `camera.mvp()` with the corrected matrix in-memory:
- Buggy matrix: NDC ≈ [-0.007, -0.002, 0.005] for globe points (dot).
- Fixed matrix: NDC x∈[0.15, 0.92], y∈[-0.88, 0.09] over the full cube-sphere mesh, **0 points culled** — a large visible disc.

### Secondary issue (correctness, not the collapse)
Defaults `near=100.0`, `far=10_000_000.0` with `distance=15_000_000.0` place the whole globe *past* the far plane (eye-to-globe distance ≈ 1.55e7–2.82e7 m). x/y framing is unaffected (so the visual fix is the matrix alone), but depth/clipping is wrong for any real renderer. `near`/`far` should span the scene at Earth scale.

`camera.py` is already wired into the pipeline (`ascii.py` passes a `Camera` into `project_ecef`, which calls `camera.mvp()` + camera-relative subtract). No wiring change needed — only the math.

`webgl_stub.html` uses its **own** orthographic unit-sphere path (lines 61–90) and is unaffected; leave it as-is.

## Changes

### 1. `aethermap/render/camera.py` — fix `projection_matrix()` (lines 81–86)
Swap `row2[3]` and `row3[2]` to the standard form:
```python
return [
    [f / aspect, 0.0, 0.0, 0.0],
    [0.0, f, 0.0, 0.0],
    [0.0, 0.0, (self.far + self.near) * nf, 2.0 * self.far * self.near * nf],
    [0.0, 0.0, -1.0, 0.0],
]
```

### 2. `aethermap/render/camera.py` — fix `Camera` defaults (lines 19–25)
Make `near`/`far` Earth-scale so the globe sits inside the depth range:
```python
near: float = 1_000_000.0      # 1e6 m
far:  float = 100_000_000.0    # 1e8 m  (globe is ~1.55e7–2.82e7 m from eye)
```
Keep `alt=500_000.0`, `distance=15_000_000.0`, `fov=60°`, default `width/height` unchanged.

### 3. (Optional) Regression test
Add `aethermap/tests/test_camera.py` (new `tests/` package under `aethermap/`) asserting the projection matrix has `-1.0` in `[3][2]` and `2*far*near*nf` in `[2][3]`, and that `project_ecef` of a globe vertex yields NDC with `|x|` and `|y|` > 0.1 (not ≈ 0). Only if a test harness already exists / is cheap to add; otherwise skip to avoid scope creep.

## Validation
1. `cd aethermap/src && python -m aethermap.render.demo` — frame should now show a large globe outline (many `.`) with `S`/`T`/`M` entities placed on it, not a lone `M`.
2. Quick numerical check (already done during diagnosis, re-run to confirm):
   ```python
   import numpy as np
   from aethermap.render.camera import Camera
   from aethermap.render.projection import cube_sphere_mesh, project_ecef
   cam = Camera()
   xs, ys = [], []
   for a, b in cube_sphere_mesh(8):
       for p in (a, b):
           r = project_ecef(p, cam)
           if r: xs.append(r[0]); ys.append(r[1])
   assert max(abs(min(xs)), abs(max(xs))) > 0.1   # was ~0.005
   assert max(abs(min(ys)), abs(max(ys))) > 0.1
   ```
3. Confirm `project_ecef` still returns `None` for vertices behind the camera (`clip[3] <= 0`) — unchanged behaviour.

## Risks / notes
- The fix is purely the matrix transpose + default scale; view matrix and `project_ecef` (camera-relative subtract) are correct and unchanged.
- `webgl_stub.html` is intentionally orthographic and independent — do not "fix" it to match.
- The globe will appear shifted (right/down) because default `pitch=-0.3` tilts the view; this is expected and tunable via `Camera.pitch`/`yaw`, not a bug.
