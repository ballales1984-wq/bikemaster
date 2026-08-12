cmake_minimum_required(VERSION 3.15)
project(AetherMap CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

FetchContent_Declare(
    glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG 3.4
)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(glfw)

FetchContent_Declare(
    glm
    GIT_REPOSITORY https://github.com/g-truc/glm.git
    GIT_TAG 1.0.1
)
FetchContent_MakeAvailable(glm)

FetchContent_Declare(
    glad
    GIT_REPOSITORY https://github.com/Dav1dde/glad.git
    GIT_TAG v2.0.8
)
set(GLAD_PROFILE "core" CACHE STRING "" FORCE)
set(GLAD_API "gl=" CACHE STRING "" FORCE)
FetchContent_MakeAvailable(glad)

add_executable(aethermap_cpp main.cpp shader.vert shader.frag)
target_link_libraries(aethermap_cpp PRIVATE glfw glad glm)

if(WIN32)
    target_link_libraries(aethermap_cpp PRIVATE opengl32)
endif()

add_custom_command(TARGET aethermap_cpp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_CURRENT_SOURCE_DIR}/shader.vert
        $<TARGET_FILE_DIR:aethermap_cpp>/shader.vert
    COMMAND ${CMAKE_COMMAND} -E copy
        ${CMAKE_CURRENT_SOURCE_DIR}/shader.frag
        $<TARGET_FILE_DIR:aethermap_cpp>/shader.frag
)
