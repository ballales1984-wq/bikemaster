#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>
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
// Camera state
// ---------------------------------------------------------------------------

static float camTheta = 0.0f;
static float camPhi = 0.4f;
static float camRadius = 3.5f;
static bool leftDown = false;
static double lastX = 0.0, lastY = 0.0;

static void mouseCallback(GLFWwindow* w, double x, double y) {
    if (leftDown) {
        float dx = float(x - lastX);
        float dy = float(y - lastY);
        camTheta -= dx * 0.01f;
        camPhi -= dy * 0.01f;
        camPhi = glm::clamp(camPhi, 0.1f, 1.5f);
    }
    lastX = x;
    lastY = y;
}

static void mouseButtonCallback(GLFWwindow* w, int button, int action, int mods) {
    if (button == GLFW_MOUSE_BUTTON_LEFT) {
        leftDown = (action == GLFW_PRESS);
    }
}

static void scrollCallback(GLFWwindow* w, double xoff, double yoff) {
    camRadius += float(yoff) * 0.1f;
    camRadius = glm::clamp(camRadius, 1.5f, 10.0f);
}

// ---------------------------------------------------------------------------
// Point cloud generation (Fibonacci sphere, ~10k points)
// ---------------------------------------------------------------------------

static std::vector<float> generatePointCloud(int count, float radius) {
    std::vector<float> data;
    data.reserve(count * 6); // x,y,z,r,g,b

    const float phi_golden = 3.14159265359f * (3.0f - sqrtf(5.0f));

    for (int i = 0; i < count; ++i) {
        float y = 1.0f - (i / float(count - 1)) * 2.0f; // 1 -> -1
        float radiusAtY = sqrtf(1.0f - y * y);
        float theta = phi_golden * i;

        float x = cosf(theta) * radiusAtY;
        float z = sinf(theta) * radiusAtY;

        x *= radius;
        y *= radius;
        z *= radius;

        // Color based on latitude (height)
        float t = (y / radius + 1.0f) * 0.5f; // 0 bottom, 1 top
        float r = t;
        float g = 0.3f + 0.4f * sinf(t * 3.14159f);
        float b = 1.0f - t * 0.5f;

        data.push_back(x);
        data.push_back(y);
        data.push_back(z);
        data.push_back(r);
        data.push_back(g);
        data.push_back(b);
    }
    return data;
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

    GLFWwindow* window = glfwCreateWindow(1280, 720, "AetherMap — Milestone 3", nullptr, nullptr);
    if (!window) {
        std::cerr << "glfwCreateWindow failed\n";
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);

    glfwSetCursorPosCallback(window, mouseCallback);
    glfwSetMouseButtonCallback(window, mouseButtonCallback);
    glfwSetScrollCallback(window, scrollCallback);

    // --- GLAD init ---
    if (!gladLoadGLLoader(reinterpret_cast<GLADloadproc>(glfwGetProcAddress))) {
        std::cerr << "gladLoadGLLoader failed\n";
        glfwTerminate();
        return -1;
    }

    std::cout << "OpenGL " << glGetString(GL_VERSION) << "\n";
    std::cout << "Vendor  " << glGetString(GL_VENDOR) << "\n";

    // --- Shaders ---
    std::string vertSrc = loadFile("shaders/basic.vert");
    std::string fragSrc = loadFile("shaders/basic.frag");
    if (vertSrc.empty() || fragSrc.empty()) return -1;

    GLuint program = linkProgram(vertSrc, fragSrc);
    if (!program) return -1;

    GLint mvpLoc = glGetUniformLocation(program, "uMVP");
    GLint pointSizeLoc = glGetUniformLocation(program, "uPointSize");

    // --- Triangle geometry (kept from Milestone 1) ---
    const float triVertices[] = {
        // position          // color (RGB)
         0.0f,  0.6f, 0.0f,  1.0f, 0.2f, 0.2f,
        -0.6f, -0.4f, 0.0f,  0.2f, 1.0f, 0.2f,
         0.6f, -0.4f, 0.0f,  0.2f, 0.4f, 1.0f,
    };

    GLuint triVAO = 0, triVBO = 0;
    glGenVertexArrays(1, &triVAO);
    glGenBuffers(1, &triVBO);

    glBindVertexArray(triVAO);
    glBindBuffer(GL_ARRAY_BUFFER, triVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(triVertices), triVertices, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    // --- Point cloud geometry ---
    constexpr int NUM_POINTS = 10000;
    constexpr float SPHERE_RADIUS = 1.5f;
    std::vector<float> pointData = generatePointCloud(NUM_POINTS, SPHERE_RADIUS);

    GLuint pointVAO = 0, pointVBO = 0;
    glGenVertexArrays(1, &pointVAO);
    glGenBuffers(1, &pointVBO);

    glBindVertexArray(pointVAO);
    glBindBuffer(GL_ARRAY_BUFFER, pointVBO);
    glBufferData(GL_ARRAY_BUFFER, pointData.size() * sizeof(float), pointData.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(0));
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), reinterpret_cast<void*>(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    // --- Render state ---
    bool renderPoints = true;
    bool spaceWasDown = false;
    glEnable(GL_DEPTH_TEST);

    // --- Render loop ---
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();

        // Spacebar toggle
        if (glfwGetKey(window, GLFW_KEY_SPACE) == GLFW_PRESS) {
            if (!spaceWasDown) {
                renderPoints = !renderPoints;
                spaceWasDown = true;
            }
        } else {
            spaceWasDown = false;
        }

        int display_w = 0, display_h = 0;
        glfwGetFramebufferSize(window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        float aspect = float(display_w) / float(display_h);

        glClearColor(0.08f, 0.08f, 0.10f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Compute camera
        glm::vec3 camPos(
            camRadius * cosf(camPhi) * sinf(camTheta),
            camRadius * sinf(camPhi),
            camRadius * cosf(camPhi) * cosf(camTheta)
        );
        glm::mat4 view = glm::lookAt(camPos, glm::vec3(0.0f), glm::vec3(0.0f, 1.0f, 0.0f));
        glm::mat4 proj = glm::perspective(glm::radians(45.0f), aspect, 0.1f, 100.0f);
        glm::mat4 mvp = proj * view;

        glUseProgram(program);
        glUniformMatrix4fv(mvpLoc, 1, GL_FALSE, glm::value_ptr(mvp));

        if (renderPoints) {
            glUniform1f(pointSizeLoc, 4.0f);
            glBindVertexArray(pointVAO);
            glDrawArrays(GL_POINTS, 0, NUM_POINTS);
        } else {
            glBindVertexArray(triVAO);
            glDrawArrays(GL_TRIANGLES, 0, 3);
        }

        glfwSwapBuffers(window);
    }

    // --- Cleanup ---
    glDeleteVertexArrays(1, &triVAO);
    glDeleteBuffers(1, &triVBO);
    glDeleteVertexArrays(1, &pointVAO);
    glDeleteBuffers(1, &pointVBO);
    glDeleteProgram(program);

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
