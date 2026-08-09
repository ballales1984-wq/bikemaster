# AetherMap C++ Renderer — Milestones 1-6 Integrated

Minimal OpenGL scaffold: window + colored triangle + point cloud + ImGui + LOD + spatial index.

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
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:\src\vcpkg\scripts\buildsystems\vcpkg.cmake
cmake --build build --config Release

# Run
.\build\Release\AetherMapRenderer.exe
```

GLAD and Dear ImGui are fetched automatically via CMake FetchContent.

## What this milestone does

1. Creates a 1280x720 GLFW window
2. Loads OpenGL 3.3 core via GLAD
3. Renders a colored triangle (Milestone 1)
4. Renders a 10k-point Fibonacci sphere with per-vertex RGB colors (Milestone 3)
5. Orbit camera with mouse drag + scroll zoom using GLM (Milestone 2)
6. CPU-side LOD selection: high/medium/low based on camera distance (Milestone 5)
7. Dear ImGui debug panel with layer switcher and LOD override (Milestone 4)
8. Spatial index header for frustum culling (Milestone 6, header-only)

## Controls

- **Left mouse drag**: rotate camera
- **Scroll wheel**: zoom in/out
- **Space**: toggle point cloud visibility
- **ImGui panel**: switch layers, adjust LOD
