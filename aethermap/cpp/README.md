# AetherMap C++ Renderer — Milestone 5

OpenGL 3.3 core renderer with CPU-side LOD selection for a procedural point cloud.

## Prerequisites

- CMake >= 3.20
- C++17 compiler (MSVC via Visual Studio Build Tools, or MinGW-w64)
- Git (for FetchContent)
- vcpkg (recommended for dependency management)

## Setup (vcpkg, recommended)

```powershell
# Bootstrap vcpkg if you don't have it
git clone https://github.com/microsoft/vcpkg.git C:\src\vcpkg
.\vcpkg\bootstrap-vcpkg.bat

# Install dependencies
.\vcpkg\vcpkg install glfw3:x64-windows
.\vcpkg\vcpkg install glm:x64-windows

# Configure (from aethermap/cpp/)
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:\src\vcpkg\scripts\buildsystems\vcpkg.cmake -Dglfw3_DIR=C:\src\vcpkg\packages\glfw3_x64-windows\share\glfw3 -Dglm_DIR=C:\src\vcpkg\packages\glm_x64-windows\share\glm "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
cmake --build build --config Release

# Run
.\build\Release\AetherMapRenderer.exe
```

GLAD is fetched automatically via CMake FetchContent (Dav1dde/glad v0.1.36).

## Manual dependency setup

If you prefer manual installs:
- GLFW: https://www.glfw.org/download.html
- GLM: https://github.com/g-truc/glm (header-only, just add include path)
- GLAD: generate at https://glad.dav1d.de/ (OpenGL, Core profile, 3.3) and place headers in `external/glad/`

## What this milestone does

1. Creates a 1280×720 GLFW window
2. Loads OpenGL 3.3 core via GLAD
3. Compiles passthrough shaders + point shaders
4. Renders a colored triangle (preserved from Milestone 1)
5. Generates a 10,000-point Fibonacci sphere point cloud
6. CPU-side LOD selection based on camera distance:
   - **High** (< 5.0 units): 100% points, size 4.0
   - **Medium** (5.0–15.0 units): 50% points, size 3.0
   - **Low** (> 15.0 units): 25% points, size 2.0
7. Minimal orbit camera (drag to rotate, scroll to zoom)
8. Spacebar toggles point cloud visibility

## Controls

- **Left mouse drag**: orbit camera
- **Scroll wheel**: zoom in/out
- **Spacebar**: toggle point cloud on/off

## Next milestones

- Dear ImGui debug panel (layer switch, LOD slider)
- Spatial index (S2 / cube-quadtree)
- GPU-side LOD / tessellation
- Terrain integration
