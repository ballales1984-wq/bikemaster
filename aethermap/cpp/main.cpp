#include <glad/glad.h>
#include <GLFW/glfw3.h>
#define IMGUI_DEFINE_MATH_OPERATORS
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"

#include <iostream>
#include <string>

// ---------------------------------------------------------------------------
// Milestone 1: triangle rendering (must remain functional)
// ---------------------------------------------------------------------------

static const char* kTriangleVert = R"(#version 330 core
layout (location = 0) in vec3 aPos;
uniform float u_lod;
void main() {
    gl_Position = vec4(aPos, 1.0);
})";

static const char* kTriangleFrag = R"(#version 330 core
out vec4 FragColor;
uniform float u_lod;
void main() {
    FragColor = vec4(0.2 + u_lod * 0.6, 0.7, 0.9, 1.0);
})";

static GLuint g_triangleVAO = 0;
static GLuint g_triangleShader = 0;
static GLint g_triangleLodLoc = -1;

static bool checkShader(GLuint id, const char* label) {
    GLint ok = 0;
    glGetShaderiv(id, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        glGetShaderiv(id, GL_INFO_LOG_LENGTH, &len);
        std::string log(len, '\0');
        glGetShaderInfoLog(id, len, nullptr, log.data());
        std::cerr << label << " compile error: " << log << '\n';
    }
    return ok != 0;
}

static bool checkProgram(GLuint id, const char* label) {
    GLint ok = 0;
    glGetProgramiv(id, GL_LINK_STATUS, &ok);
    if (!ok) {
        GLint len = 0;
        glGetProgramiv(id, GL_INFO_LOG_LENGTH, &len);
        std::string log(len, '\0');
        glGetProgramInfoLog(id, len, nullptr, log.data());
        std::cerr << label << " link error: " << log << '\n';
    }
    return ok != 0;
}

static void initTriangle() {
    float verts[] = {
        -0.5f, -0.5f, 0.0f,
         0.5f, -0.5f, 0.0f,
         0.0f,  0.5f, 0.0f,
    };
    GLuint vbo = 0;
    glGenVertexArrays(1, &g_triangleVAO);
    glGenBuffers(1, &vbo);
    glBindVertexArray(g_triangleVAO);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &kTriangleVert, nullptr);
    glCompileShader(vs);
    checkShader(vs, "triangle VS");

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &kTriangleFrag, nullptr);
    glCompileShader(fs);
    checkShader(fs, "triangle FS");

    g_triangleShader = glCreateProgram();
    glAttachShader(g_triangleShader, vs);
    glAttachShader(g_triangleShader, fs);
    glLinkProgram(g_triangleShader);
    checkProgram(g_triangleShader, "triangle program");

    glDeleteShader(vs);
    glDeleteShader(fs);

    g_triangleLodLoc = glGetUniformLocation(g_triangleShader, "u_lod");
}

static void renderTriangle(float lod) {
    glUseProgram(g_triangleShader);
    if (g_triangleLodLoc >= 0) glUniform1f(g_triangleLodLoc, lod);
    glBindVertexArray(g_triangleVAO);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glBindVertexArray(0);
}

// ---------------------------------------------------------------------------
// Milestone 3 stub: point cloud (placeholder for m3/m5 integration)
// ---------------------------------------------------------------------------

static const char* kPointVert = R"(#version 330 core
layout (location = 0) in vec3 aPos;
uniform float u_lod;
void main() {
    gl_Position = vec4(aPos, 1.0);
    gl_PointSize = 3.0 + u_lod * 5.0;
})";

static const char* kPointFrag = R"(#version 330 core
out vec4 FragColor;
void main() {
    FragColor = vec4(1.0, 0.4, 0.1, 1.0);
})";

static GLuint g_pointVAO = 0;
static GLuint g_pointShader = 0;

static void initPointCloud() {
    float pts[] = {
        -0.6f,  0.6f, 0.0f,
        -0.3f,  0.3f, 0.0f,
         0.0f,  0.0f, 0.0f,
         0.3f, -0.3f, 0.0f,
         0.6f, -0.6f, 0.0f,
    };
    GLuint vbo = 0;
    glGenVertexArrays(1, &g_pointVAO);
    glGenBuffers(1, &vbo);
    glBindVertexArray(g_pointVAO);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(pts), pts, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    GLuint vs = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vs, 1, &kPointVert, nullptr);
    glCompileShader(vs);
    checkShader(vs, "point VS");

    GLuint fs = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fs, 1, &kPointFrag, nullptr);
    glCompileShader(fs);
    checkShader(fs, "point FS");

    g_pointShader = glCreateProgram();
    glAttachShader(g_pointShader, vs);
    glAttachShader(g_pointShader, fs);
    glLinkProgram(g_pointShader);
    checkProgram(g_pointShader, "point program");

    glDeleteShader(vs);
    glDeleteShader(fs);
}

static void renderPointCloud(float /*lod*/) {
    glUseProgram(g_pointShader);
    glBindVertexArray(g_pointVAO);
    glDrawArrays(GL_POINTS, 0, 5);
    glBindVertexArray(0);
}

// ---------------------------------------------------------------------------
// Milestone 4: Dear ImGui debug panel
// ---------------------------------------------------------------------------

static bool g_showDebugPanel = true;
static int g_layerMode = 0; // 0 = Triangle, 1 = Point Cloud, 2 = Both
static float g_lodValue = 0.0f;

static void renderDebugPanel() {
    if (!g_showDebugPanel) return;

    ImGui::Begin("AetherMap Debug", &g_showDebugPanel);

    const char* layers[] = { "Triangle", "Point Cloud", "Both" };
    ImGui::Combo("Layer", &g_layerMode, layers, 3);

    ImGui::SliderFloat("LOD", &g_lodValue, 0.0f, 1.0f);
    ImGui::Text("LOD value: %.3f", g_lodValue);

    ImGui::End();
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

int main() {
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW\n";
        return -1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(1280, 720, "AetherMap C++ Renderer", nullptr, nullptr);
    if (!window) {
        std::cerr << "Failed to create GLFW window\n";
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cerr << "Failed to initialize GLAD\n";
        return -1;
    }

    // Milestone 1: initialize triangle (preserved)
    initTriangle();

    // Milestone 3: initialize point cloud stub
    initPointCloud();

    // Milestone 4: initialize Dear ImGui
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    ImGui::StyleColorsDark();
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 330 core");

    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        // Milestone 4: start ImGui frame
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();

        // Milestone 1: render scene (triangle + optional point cloud)
        glClearColor(0.08f, 0.08f, 0.08f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        if (g_layerMode == 0 || g_layerMode == 2) {
            renderTriangle(g_lodValue);
        }
        if (g_layerMode == 1 || g_layerMode == 2) {
            renderPointCloud(g_lodValue);
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

    // Cleanup
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();

    glDeleteVertexArrays(1, &g_triangleVAO);
    glDeleteProgram(g_triangleShader);
    glDeleteVertexArrays(1, &g_pointVAO);
    glDeleteProgram(g_pointShader);

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
