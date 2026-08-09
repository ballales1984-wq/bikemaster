# AetherMap C++ Renderer — Milestone 1

Minimal OpenGL scaffold: window + colored triangle.

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

GLAD is fetched automatically via CMake FetchContent (Dav1dde/glad v0.1.36).

## Manual dependency setup

If you prefer manual installs:
- GLFW: https://www.glfw.org/download.html
- GLM: https://github.com/g-truc/glm (header-only, just add include path)
- GLAD: generate at https://glad.dav1d.de/ (OpenGL, Core profile, 3.3) and place headers in `external/glad/`

## What this milestone does

1. Creates a 1280×720 GLFW window
2. Loads OpenGL 3.3 core via GLAD
3. Compiles a passthrough vertex shader + flat-color fragment shader
4. Renders a single RGB triangle

## Next milestones

- Camera orbit (glm mat4, GLFW scroll/drag)
- Point cloud render (GL_POINTS, attribute-driven color)
- Dear ImGui debug panel (layer switch, LOD slider)
- LOD CPU-side selection
- Spatial index (S2 / cube-quadtree)
