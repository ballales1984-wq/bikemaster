cmake_minimum_required(VERSION 3.20)
project(AetherMapRenderer LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- Dependencies ----

# GLFW
find_package(glfw3 REQUIRED)

# OpenGL
find_package(OpenGL REQUIRED)

# GLM (header-only)
find_package(glm CONFIG REQUIRED)

# GLAD loader (FetchContent)
include(FetchContent)
FetchContent_Declare(
  glad
  GIT_REPOSITORY https://github.com/Dav1dde/glad.git
  GIT_TAG        v0.1.36
)
# Force glad2 to generate a Core 3.3 C loader
set(FETCHCONTENT_QUIET OFF)
set(GLAD_PROFILE "core" CACHE STRING "" FORCE)
set(GLAD_API "gl=3.3" CACHE STRING "" FORCE)
set(GLAD_GENERATOR "c" CACHE STRING "" FORCE)
set(GLAD_EXTENSIONS "" CACHE STRING "" FORCE)
FetchContent_MakeAvailable(glad)

# ---- Executable ----

add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} PRIVATE
  glfw
  OpenGL::GL
  glad::glad
  glm::glm
)

# ---- Shaders: copy to build dir at build time ----

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory
  ${CMAKE_SOURCE_DIR}/shaders
  $<TARGET_FILE_DIR:${PROJECT_NAME}>/shaders
  COMMENT "Copying shaders to build directory"
)
