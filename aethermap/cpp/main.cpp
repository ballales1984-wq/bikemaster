#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>

struct Shader
{
    GLuint id = 0;
    GLuint mvpLoc = -1;

    static std::string loadFile(const std::string& path)
    {
        std::ifstream f(path);
        if (!f.is_open())
        {
            std::cerr << "Failed to open shader: " << path << "\n";
            return {};
        }
        std::stringstream ss;
        ss << f.rdbuf();
        return ss.str();
    }

    static GLuint compile(GLenum type, const std::string& src)
    {
        GLuint s = glCreateShader(type);
        const char* c = src.c_str();
        glShaderSource(s, 1, &c, nullptr);
        glCompileShader(s);
        GLint ok = 0;
        glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
        if (!ok)
        {
            char log[512];
            glGetShaderInfoLog(s, 512, nullptr, log);
            std::cerr << "Shader compile error: " << log << "\n";
            glDeleteShader(s);
            return 0;
        }
        return s;
    }

    bool build(const std::string& vertPath, const std::string& fragPath)
    {
        GLuint vs = compile(GL_VERTEX_SHADER, loadFile(vertPath));
        GLuint fs = compile(GL_FRAGMENT_SHADER, loadFile(fragPath));
        if (!vs || !fs) return false;

        id = glCreateProgram();
        glAttachShader(id, vs);
        glAttachShader(id, fs);
        glLinkProgram(id);

        GLint ok = 0;
        glGetProgramiv(id, GL_LINK_STATUS, &ok);
        if (!ok)
        {
            char log[512];
            glGetProgramInfoLog(id, 512, nullptr, log);
            std::cerr << "Program link error: " << log << "\n";
            glDeleteProgram(id);
            id = 0;
            glDeleteShader(vs);
            glDeleteShader(fs);
            return false;
        }

        glDeleteShader(vs);
        glDeleteShader(fs);
        mvpLoc = glGetUniformLocation(id, "uMVP");
        return true;
    }

    void use() const { glUseProgram(id); }
};

struct OrbitCamera
{
    glm::vec3 target = glm::vec3(0.0f, 0.0f, 0.0f);
    float azimuth = glm::radians(45.0f);
    float elevation = glm::radians(30.0f);
    float distance = 6.0f;
    float minDistance = 1.0f;
    float maxDistance = 50.0f;

    float rotateSpeed = 0.005f;
    float dollySpeed = 0.1f;
    float panSpeed = 0.02f;

    glm::vec3 getPosition() const
    {
        glm::vec3 offset;
        offset.x = distance * std::cos(elevation) * std::sin(azimuth);
        offset.y = distance * std::sin(elevation);
        offset.z = distance * std::cos(elevation) * std::cos(azimuth);
        return target + offset;
    }

    glm::mat4 getView() const
    {
        return glm::lookAt(getPosition(), target, glm::vec3(0.0f, 1.0f, 0.0f));
    }

    glm::mat4 getProjection(float aspect) const
    {
        return glm::perspective(glm::radians(45.0f), aspect, 0.1f, 100.0f);
    }

    glm::mat4 getVP(float aspect) const
    {
        return getProjection(aspect) * getView();
    }

    glm::vec3 getRight() const
    {
        glm::vec3 forward = glm::normalize(target - getPosition());
        return glm::normalize(glm::cross(glm::vec3(0.0f, 1.0f, 0.0f), forward));
    }

    glm::vec3 getUp() const
    {
        glm::vec3 forward = glm::normalize(target - getPosition());
        return glm::normalize(glm::cross(forward, getRight()));
    }

    void rotate(float dx, float dy)
    {
        azimuth -= dx * rotateSpeed;
        elevation += dy * rotateSpeed;
        elevation = glm::clamp(elevation, glm::radians(-89.0f), glm::radians(89.0f));
    }

    void dolly(float dy)
    {
        distance *= (1.0f + dy * dollySpeed);
        distance = glm::clamp(distance, minDistance, maxDistance);
    }

    void pan(float dx, float dy)
    {
        target += getRight() * dx * panSpeed * distance;
        target += getUp() * dy * panSpeed * distance;
    }
};

int main()
{
    if (!glfwInit())
    {
        std::cerr << "Failed to init GLFW\n";
        return -1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    GLFWwindow* window = glfwCreateWindow(1280, 720, "AetherMap C++ - Milestone 2", nullptr, nullptr);
    if (!window)
    {
        std::cerr << "Failed to create window\n";
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cerr << "Failed to init GLAD\n";
        glfwTerminate();
        return -1;
    }

    glEnable(GL_DEPTH_TEST);

    float vertices[] = {
        -0.5f, -0.5f, 0.0f,  1.0f, 0.2f, 0.3f,
         0.5f, -0.5f, 0.0f,  0.2f, 1.0f, 0.3f,
         0.0f,  0.5f, 0.0f,  0.2f, 0.4f, 1.0f
    };

    GLuint vao, vbo;
    glGenVertexArrays(1, &vao);
    glGenBuffers(1, &vbo);
    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glBindVertexArray(0);

    Shader shader;
    if (!shader.build("shader.vert", "shader.frag"))
    {
        std::cerr << "Failed to build shader\n";
        return -1;
    }

    OrbitCamera camera;

    bool leftDown = false;
    double lastX = 0.0, lastY = 0.0;

    glfwSetMouseButtonCallback(window, [](GLFWwindow* w, int button, int action, int mods)
    {
        if (button == GLFW_MOUSE_BUTTON_LEFT)
        {
            if (action == GLFW_PRESS)
            {
                glfwSetInputMode(w, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
                glfwGetCursorPos(w, &lastX, &lastY);
            }
            else if (action == GLFW_RELEASE)
            {
                glfwSetInputMode(w, GLFW_CURSOR, GLFW_CURSOR_NORMAL);
            }
        }
    });

    glfwSetScrollCallback(window, [](GLFWwindow* w, double xoff, double yoff)
    {
        OrbitCamera* cam = (OrbitCamera*)glfwGetWindowUserPointer(w);
        if (cam) cam->dolly((float)yoff);
    });

    glfwSetWindowUserPointer(window, &camera);

    std::cout << "AetherMap C++ Milestone 2 - Camera Orbit Controls\n";
    std::cout << "Drag with left mouse button to orbit\n";
    std::cout << "Scroll to zoom\n";
    std::cout << "WASD / Arrow keys to pan\n";

    while (!glfwWindowShouldClose(window))
    {
        int width, height;
        glfwGetFramebufferSize(window, &width, &height);
        glViewport(0, 0, width, height);
        glClearColor(0.08f, 0.08f, 0.12f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        if (glfwGetMouseButton(window, GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS)
        {
            double x, y;
            glfwGetCursorPos(window, &x, &y);
            float dx = (float)(x - lastX);
            float dy = (float)(y - lastY);
            camera.rotate(dx, dy);
            lastX = x;
            lastY = y;
        }

        float panX = 0.0f, panY = 0.0f;
        if (glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_UP) == GLFW_PRESS)
            panY += 1.0f;
        if (glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_DOWN) == GLFW_PRESS)
            panY -= 1.0f;
        if (glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_LEFT) == GLFW_PRESS)
            panX -= 1.0f;
        if (glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS || glfwGetKey(window, GLFW_KEY_RIGHT) == GLFW_PRESS)
            panX += 1.0f;
        if (panX != 0.0f || panY != 0.0f)
            camera.pan(panX, panY);

        glm::mat4 vp = camera.getVP(width / (float)height);
        shader.use();
        glUniformMatrix4fv(shader.mvpLoc, 1, GL_FALSE, glm::value_ptr(vp));

        glBindVertexArray(vao);
        glDrawArrays(GL_TRIANGLES, 0, 3);
        glBindVertexArray(0);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glDeleteVertexArrays(1, &vao);
    glDeleteBuffers(1, &vbo);
    glDeleteProgram(shader.id);

    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
