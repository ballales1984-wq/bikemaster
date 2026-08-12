# AetherMap C++ Renderer

Milestone 2 — Camera Orbit Controls.

## What was added

- **Orbit camera** (`OrbitCamera` in `main.cpp`): azimuth/elevation spherical coordinates around a target point, with `glm::lookAt` and `glm::perspective`.
- **Mouse drag (left button)**: rotates the camera around the target (azimuth + elevation). Uses cursor capture for smooth continuous drag.
- **Scroll wheel**: dolly in/out along the view direction, clamped between `minDistance` and `maxDistance`.
- **WASD / Arrow keys**: pan the camera target left/right/up/down relative to the current view orientation.
- **View-projection uniform**: the combined VP matrix is passed to the vertex shader as `uMVP` each frame.

## Controls

| Input | Action |
|-------|--------|
| Left mouse drag | Orbit (rotate) |
| Scroll wheel | Zoom (dolly) |
| W / S or Up / Down | Pan |
| A / D or Left / Right | Pan |

## Build

```bash
cmake -B build -S aethermap/cpp
cmake --build build --config Release
```

Requires a working internet connection the first time (FetchContent downloads GLFW, GLM, and glad2).
