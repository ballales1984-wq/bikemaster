#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#define IMGUI_DEFINE_MATH_OPERATORS
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

// ---------------------------------------------------------------------------
// Shader utilities
// ---------------------------------------------------------------------------

static std::string loadFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) {
        std::cerr << "Failed to open: " << path << "\n";
        return {};
    }
    std::stringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static GLuint compileShader(GLenum type, const std::string& source) {
    GLuint shader = glCreateShader(type);
    const char* src = source.c_str();
    glShaderSource(shader, 1, &src, nullptr);
    glCompileShader(shader);

    GLint ok = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[512] = {};
        glGetShaderInfoLog(shader, sizeof(log), nullptr, log);
        std::cerr << "Shader compile error:\n" << log << "\n";
        glDeleteShader(shader);
        return 0;
    }
    return shader;
}

static GLuint linkProgram(const std::string& vertSrc, const std::string& fragSrc) {
    GLuint vs = compileShader(GL_VERTEX_SHADER, vertSrc);
    GLuint fs = compileShader(GL_FRAGMENT_SHADER, fragSrc);
    if (!vs || !fs) return 0;

    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);

    GLint ok = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[512] = {};
        glGetProgramInfoLog(prog, sizeof(log), nullptr, log);
        std::cerr << "Program link error:\n" << log << "\n";
        glDeleteProgram(prog);
        prog = 0;
    }

    glDeleteShader(vs);
    glDeleteShader(fs);
    return prog;
}

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------

struct Camera {
    float azimuth = 0.0f;
    float elevation = 0.5f;
    float radius = 8.0f;
    float minRadius = 2.0f;
    float maxRadius = 50.0f;

    glm::vec3 getPosition() const {
        return glm::vec3(
            radius * cosf(elevation) * sinf(azimuth),
            radius * sinf(elevation),
            radius * cosf(elevation) * cosf(azimuth)
        );
    }

    glm::mat4 getViewMatrix() const {
        return glm::lookAt(getPosition(), glm::vec3(0.0f), glm::vec3(0.0f, 1.0f, 0.0f));
    }
};

static Camera g_camera;
static bool g_leftDown = false;
static double g_lastX = 0.0;
static double g_lastY = 0.0;
static bool g_showPoints = true;

static void mouseCallback(GLFWwindow* window, int button, int action, int mods) {
    if (button == GLFW_MOUSE_BUTTON_LEFT) {
        g_leftDown = (action == GLFW_PRESS);
        if (g_leftDown) {
            glfwGetCursorPos(window, &g_lastX, &g_lastY);
        }
    }
}

static void cursorCallback(GLFWwindow* window, double x, double y) {
    if (!g_leftDown) return;
    double dx = x - g_lastX;
    double dy = y - g_lastY;
    g_lastX = x;
    g_lastY = y;

    g_camera.azimuth += float(dx) * 0.005f;
    g_camera.elevation += float(dy) * 0.005f;
    g_camera.elevation = glm::clamp(g_camera.elevation, -1.5f, 1.5f);
}

static void scrollCallback(GLFWwindow* window, double x, double y) {
    g_camera.radius += float(y) * 0.5f;
    g_camera.radius = glm::clamp(g_camera.radius, g_camera.minRadius, g_camera.maxRadius);
}

static void keyCallback(GLFWwindow* window, int key, int scancode, int action, int mods) {
    if (key == GLFW_KEY_SPACE && action == GLFW_PRESS) {
        g_showPoints = !g_showPoints;
    }
}

// ---------------------------------------------------------------------------
// Point cloud
// ---------------------------------------------------------------------------

struct PointCloud {
    std::vector<float> vertices;
    GLuint vao = 0;
    GLuint vbo = 0;
    GLuint eboHigh = 0;
    GLuint eboMedium = 0;
    GLuint eboLow = 0;
    int countHigh = 0;
    int countMedium = 0;
    int countLow = 0;
};

static PointCloud generatePointCloud(int numPoints) {
    PointCloud pc;
    const float R = 2.0f;
    const float phi = (1.0f + sqrtf(5.0f));

    for (int i = 0; i < numPoints; ++i) {
        float y = 1.0f - (2.0f * i / float(numPoints - 1));
        float r = sqrtf(1.0f - y * y);
        float theta = phi * float(i);
        float x = cosf(theta) * r;
        float z = sinf(theta) * r;

        float cr = (x * R + R) / (2.0f * R);
        float cg = (y * R + R) / (2.0f * R);
        float cb = (z * R + R) / (2.0f * R);

        pc.vertices.push_back(x * R);
        pc.vertices.push_back(y * R);
        pc.vertices.push_back(z * R);
        pc.vertices.push_back(cr);
        pc.vertices.push_back(cg);
        pc.vertices.push_back(cb);
    }

    glGenVertexArrays(1, &pc.vao);
    glGenBuffers(1, &pc.vbo);
    glGenBuffers(1, &pc.eboHigh);
    glGenBuffers(1, &pc.eboMedium);
    glGenBuffers(1, &pc.eboLow);

    glBindVertexArray(pc.vao);

    glBindBuffer(GL_ARRAY_BUFFER, pc.vbo);
    glBufferData(GL_ARRAY_BUFFER, pc.vertices.size() * sizeof(float), pc.vertices.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    std::vector<unsigned int> idxHigh(numPoints);
    for (int i = 0; i < numPoints; ++i) idxHigh[i] = i;
    pc.countHigh = numPoints;
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, pc.eboHigh);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, idxHigh.size() * sizeof(unsigned int), idxHigh.data(), GL_STATIC_DRAW);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);

    std::vector<unsigned int> idxMedium;
    for (int i = 0; i < numPoints; i += 2) idxMedium.push_back(i);
    pc.countMedium = static_cast<int>(idxMedium.size());
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, pc.eboMedium);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, idxMedium.size() * sizeof(unsigned int), idxMedium.data(), GL_STATIC_DRAW);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);

    std::vector<unsigned int> idxLow;
    for (int i = 0; i < numPoints; i += 4) idxLow.push_back(i);
    pc.countLow = static_cast<int>(idxLow.size());
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, pc.eboLow);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, idxLow.size() * sizeof(unsigned int), idxLow.data(), GL_STATIC_DRAW);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0);

    return pc;
}

// ---------------------------------------------------------------------------
// LOD selection
// ---------------------------------------------------------------------------

static int selectLOD(const Camera& cam) {
    float dist = glm::length(cam.getPosition() - glm::vec3(0.0f));
    if (dist < 5.0f) return 2;       // high
    if (dist < 15.0f) return 1;      // medium
    return 0;                        // low
}

// ---------------------------------------------------------------------------
// Milestone 4: Dear ImGui debug panel
// ---------------------------------------------------------------------------

static bool g_showDebugPanel = true;
static int g_layerMode = 2; // 0 = Triangle, 1 = Point Cloud, 2 = Both

static void renderDebugPanel() {
    if (!g_showDebugPanel) return;

    ImGui::Begin("AetherMap Debug", &g_showDebugPanel);

    const char* layers[] = { "Triangle", "Point Cloud", "Both" };
    ImGui::Combo("Layer", &g_layerMode, layers, 3);

    ImGui::SliderFloat("LOD override", &g_camera.radius, g_camera.minRadius, g_camera.maxRadius);

    ImGui::Text("Points visible: %s", g_showPoints ? "yes" : "no");
    ImGui::Text("Press Space to toggle points");

    ImGui::End();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main() {
    // --- GLFW init ---
    if (!glfwInit()) {
        std::cerr << "glfwInit failed\n";
        return -1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(1280, 720, "AetherMap — Milestone 5+4", nullptr, nullptr);
    if (!window) {
        std::cerr << "glfwCreateWindow failed\n";
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);

    glfwSetMouseButtonCallback(window, mouseCallback);
    glfwSetCursorPosCallback(window, cursorCallback);
    glfwSetScrollCallback(window, scrollCallback);
    glfwSetKeyCallback(window, keyCallback);

    // --- GLAD init ---
    if (!gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))) {
        std::cerr << "gladLoadGLLoader failed\n";
        glfwTerminate();
        return -1;
    }

    std::cout << "OpenGL " << glGetString(GL_VERSION) << "\n";
    std::cout << "Vendor  " << glGetString(GL_VENDOR) << "\n";

    // --- Milestone 4: initialize Dear ImGui ---
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    ImGui::StyleColorsDark();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 330 core");

    // --- Triangle shaders & geometry (preserved from Milestone 1) ---
    std::string vertSrc = loadFile("shaders/basic.vert");
    std::string fragSrc = loadFile("shaders/basic.frag");
    if (vertSrc.empty() || fragSrc.empty()) return -1;

    GLuint program = linkProgram(vertSrc, fragSrc);
    if (!program) return -1;

    const float vertices[] = {
         0.0f,  0.6f, 0.0f,  1.0f, 0.2f, 0.2f,
        -0.6f, -0.4f, 0.0f,  0.2f, 1.0f, 0.2f,
         0.6f, -0.4f, 0.0f,  0.2f, 0.4f, 1.0f,
    };

    GLuint vao = 0, vbo = 0;
    glGenVertexArrays(1, &vao);
    glGenBuffers(1, &vbo);

    glBindVertexArray(vao);

    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    // --- Point shaders & geometry (Milestone 5) ---
    std::string pointVertSrc = loadFile("shaders/point.vert");
    std::string pointFragSrc = loadFile("shaders/point.frag");
    if (pointVertSrc.empty() || pointFragSrc.empty()) return -1;

    GLuint pointProgram = linkProgram(pointVertSrc, pointFragSrc);
    if (!pointProgram) return -1;

    PointCloud cloud = generatePointCloud(10000);

    // --- Render loop ---
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        int display_w = 0, display_h = 0;
        glfwGetFramebufferSize(window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);

        glClearColor(0.08f, 0.08f, 0.10f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        // Milestone 4: start ImGui frame
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        // Triangle
        if (g_layerMode == 0 || g_layerMode == 2) {
            glUseProgram(program);
            glBindVertexArray(vao);
            glDrawArrays(GL_TRIANGLES, 0, 3);
        }

        // Point cloud with LOD
        if ((g_layerMode == 1 || g_layerMode == 2) && g_showPoints) {
            int lod = selectLOD(g_camera);
            GLuint ebo = cloud.eboLow;
            int count = cloud.countLow;
            float pointSize = 2.0f;
            if (lod == 1) {
                ebo = cloud.eboMedium;
                count = cloud.countMedium;
                pointSize = 3.0f;
            } else if (lod == 2) {
                ebo = cloud.eboHigh;
                count = cloud.countHigh;
                pointSize = 4.0f;
            }

            glUseProgram(pointProgram);
            glm::mat4 view = g_camera.getViewMatrix();
            glUniformMatrix4fv(glGetUniformLocation(pointProgram, "uView"), 1, GL_FALSE, &view[0][0]);
            glUniform1f(glGetUniformLocation(pointProgram, "uPointSize"), pointSize);

            glBindVertexArray(cloud.vao);
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo);
            glDrawElements(GL_POINTS, count, GL_UNSIGNED_INT, nullptr);

            std::string title = "AetherMap — Milestone 5+4 | Points: " + std::to_string(count) + " | Space: toggle";
            glfwSetWindowTitle(window, title.c_str());
        } else {
            glfwSetWindowTitle(window, "AetherMap — Milestone 5+4 | Points: 0 (hidden) | Space: toggle");
        }

        // Milestone 4: render debug panel
        renderDebugPanel();

        // Milestone 4: ImGui render + platform windows update
        ImGui::Render();
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());

        if (io.ConfigFlags & ImGuiConfigFlags_ViewportsEnable) {
            GLFWwindow* backup = glfwGetCurrentContext();
            ImGui::UpdatePlatformWindows();
            ImGui::RenderPlatformWindowsDefault();
            glfwMakeContextCurrent(backup);
        }

        glfwSwapBuffers(window);
    }

    // --- Cleanup ---
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();

    glDeleteVertexArrays(1, &vao);
    glDeleteBuffers(1, &vbo);
    glDeleteProgram(program);

    glDeleteVertexArrays(1, &cloud.vao);
    glDeleteBuffers(1, &cloud.vbo);
    glDeleteBuffers(1, &cloud.eboHigh);
    glDeleteBuffers(1, &cloud.eboMedium);
    glDeleteBuffers(1, &cloud.eboLow);
    glDeleteProgram(pointProgram);

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
