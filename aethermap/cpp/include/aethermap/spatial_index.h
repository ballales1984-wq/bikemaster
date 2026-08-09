#pragma once

/*
 * AetherMap C++ Spatial Index — Milestone 6
 *
 * Lightweight, header-only 3D uniform grid spatial index for point clouds.
 * No external dependencies beyond the C++17 standard library.
 *
 * Design goals:
 *   - Store point indices in spatial cells for fast frustum culling
 *   - Match AetherMap's ECEF camera-relative coordinate convention
 *   - Integrate-ready for future LOD selection (Milestone 5 / Phase 4)
 *
 * Coordinate system:
 *   ECEF (Earth-Centered, Earth-Fixed) in meters — same as Python core/coordinates.py
 *   Camera-relative rendering: subtract camera ECEF origin before projection
 */

#define _USE_MATH_DEFINES
#include <vector>
#include <array>
#include <cmath>
#include <algorithm>
#include <unordered_map>
#include <cstdint>
#include <limits>
#include <numeric>

namespace aethermap {

// ============================================================================
// WGS-84 ellipsoid parameters (matching core/coordinates.py)
// ============================================================================
constexpr double WGS84_A       = 6378137.0;
constexpr double WGS84_F       = 1.0 / 298.257223563;
constexpr double WGS84_E2      = WGS84_F * (2.0 - WGS84_F);
constexpr double EARTH_RADIUS  = 6371008.8;

// ============================================================================
// Math primitives
// ============================================================================

struct Vec3 {
    float x, y, z;
    Vec3() = default;
    Vec3(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}

    Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Vec3 operator*(float s)        const { return {x*s, y*s, z*s}; }
    Vec3& operator+=(const Vec3& o) { x+=o.x; y+=o.y; z+=o.z; return *this; }

    float length()  const { return std::sqrt(x*x + y*y + z*z); }
    Vec3  normalized() const { float l = length(); return l > 1e-8f ? *this * (1.0f/l) : Vec3{}; }
    float dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }
    Vec3 cross(const Vec3& o) const {
        return { y*o.z - z*o.y, z*o.x - x*o.z, x*o.y - y*o.x };
    }
};

struct Vec3d {
    double x, y, z;
    Vec3d() = default;
    Vec3d(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}

    Vec3 to_float() const { return {static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)}; }
};

// ============================================================================
// 4x4 matrix — column-major (matches OpenGL / Python render/projection.py)
// ============================================================================
struct Mat4 {
    float m[16];

    float operator[](size_t i) const { return m[i]; }
    float& operator[](size_t i) { return m[i]; }

    static Mat4 identity() {
        Mat4 r{};
        r.m[0] = r.m[5] = r.m[10] = r.m[15] = 1.0f;
        return r;
    }

    bool operator==(const Mat4& o) const {
        for (int i = 0; i < 16; ++i)
            if (std::fabs(m[i] - o.m[i]) > 1e-6f) return false;
        return true;
    }

    // Matrix multiply: this * other (both column-major)
    Mat4 operator*(const Mat4& o) const {
        Mat4 r{};
        for (int col = 0; col < 4; ++col)
            for (int row = 0; row < 4; ++row) {
                float sum = 0.0f;
                for (int k = 0; k < 4; ++k)
                    sum += m[k*4 + row] * o.m[col*4 + k];
                r.m[col*4 + row] = sum;
            }
        return r;
    }

    // Transform a point (homogeneous divide)
    Vec3 transform_point(const Vec3& p) const {
        float x = m[0]*p.x + m[4]*p.y + m[8]*p.z  + m[12];
        float y = m[1]*p.x + m[5]*p.y + m[9]*p.z  + m[13];
        float z = m[2]*p.x + m[6]*p.y + m[10]*p.z + m[14];
        float w = m[3]*p.x + m[7]*p.y + m[11]*p.z + m[15];
        return {x/w, y/w, z/w};
    }

    // Transform a direction (no translation)
    Vec3 transform_direction(const Vec3& p) const {
        return {
            m[0]*p.x + m[4]*p.y + m[8]*p.z,
            m[1]*p.x + m[5]*p.y + m[9]*p.z,
            m[2]*p.x + m[6]*p.y + m[10]*p.z
        };
    }

    // General-purpose 4x4 inverse (cofactor expansion, column-major)
    Mat4 inverse() const {
        const float* a = m;
        Mat4 r;
        float* b = r.m;

        b[0]  = a[5]*(a[10]*a[15]-a[11]*a[14]) - a[9]*(a[6]*a[15]-a[7]*a[14]) + a[13]*(a[6]*a[11]-a[7]*a[10]);
        b[1]  = -(a[1]*(a[10]*a[15]-a[11]*a[14]) - a[9]*(a[2]*a[15]-a[3]*a[14]) + a[13]*(a[2]*a[11]-a[3]*a[10]));
        b[2]  = a[1]*(a[6]*a[15]-a[7]*a[14]) - a[5]*(a[2]*a[15]-a[3]*a[14]) + a[13]*(a[2]*a[7]-a[3]*a[6]);
        b[3]  = -(a[1]*(a[6]*a[11]-a[7]*a[10]) - a[5]*(a[2]*a[11]-a[3]*a[10]) + a[9]*(a[2]*a[7]-a[3]*a[6]));

        b[4]  = -(a[4]*(a[10]*a[15]-a[11]*a[14]) - a[8]*(a[6]*a[15]-a[7]*a[14]) + a[12]*(a[6]*a[11]-a[7]*a[10]));
        b[5]  = a[0]*(a[10]*a[15]-a[11]*a[14]) - a[8]*(a[2]*a[15]-a[3]*a[14]) + a[12]*(a[2]*a[11]-a[3]*a[10]);
        b[6]  = -(a[0]*(a[6]*a[15]-a[7]*a[14]) - a[4]*(a[2]*a[15]-a[3]*a[14]) + a[12]*(a[2]*a[7]-a[3]*a[6]));
        b[7]  = a[0]*(a[6]*a[11]-a[7]*a[10]) - a[4]*(a[2]*a[11]-a[3]*a[10]) + a[8]*(a[2]*a[7]-a[3]*a[6]);

        b[8]  = a[4]*(a[9]*a[15]-a[11]*a[13]) - a[8]*(a[5]*a[15]-a[7]*a[13]) + a[12]*(a[5]*a[11]-a[7]*a[9]);
        b[9]  = -(a[0]*(a[9]*a[15]-a[11]*a[13]) - a[8]*(a[1]*a[15]-a[3]*a[13]) + a[12]*(a[1]*a[11]-a[3]*a[9]));
        b[10] = a[0]*(a[5]*a[15]-a[7]*a[13]) - a[4]*(a[1]*a[15]-a[3]*a[13]) + a[12]*(a[1]*a[7]-a[3]*a[5]);
        b[11] = -(a[0]*(a[5]*a[11]-a[7]*a[9]) - a[4]*(a[1]*a[11]-a[3]*a[9]) + a[8]*(a[1]*a[7]-a[3]*a[5]));

        b[12] = -(a[4]*(a[9]*a[14]-a[10]*a[13]) - a[8]*(a[5]*a[14]-a[6]*a[13]) + a[12]*(a[5]*a[10]-a[6]*a[9]));
        b[13] = a[0]*(a[9]*a[14]-a[10]*a[13]) - a[8]*(a[1]*a[14]-a[2]*a[13]) + a[12]*(a[1]*a[10]-a[2]*a[9]);
        b[14] = -(a[0]*(a[5]*a[14]-a[6]*a[13]) - a[4]*(a[1]*a[14]-a[2]*a[13]) + a[12]*(a[1]*a[6]-a[2]*a[5]));
        b[15] = a[0]*(a[5]*a[10]-a[6]*a[9]) - a[4]*(a[1]*a[10]-a[2]*a[9]) + a[8]*(a[1]*a[6]-a[2]*a[5]);

        float det = a[0]*b[0] + a[4]*b[1] + a[8]*b[2] + a[12]*b[3];
        if (std::fabs(det) < 1e-8f) return Mat4::identity();
        float idet = 1.0f / det;
        for (int i = 0; i < 16; ++i) b[i] *= idet;
        return r;
    }
};

// ============================================================================
// Coordinate conversion — matching core/coordinates.py
// ============================================================================

struct Geodetic {
    double lat, lon, alt;
    Geodetic() = default;
    Geodetic(double lat_, double lon_, double alt_ = 0.0)
        : lat(lat_), lon(lon_), alt(alt_) {}
};

struct ECEF {
    double x, y, z;
    ECEF() = default;
    ECEF(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}

    Vec3 to_float() const { return {static_cast<float>(x), static_cast<float>(y), static_cast<float>(z)}; }
};

inline ECEF geodetic_to_ecef(double lat, double lon, double alt = 0.0) {
    double lat_r = lat * M_PI / 180.0;
    double lon_r = lon * M_PI / 180.0;
    double sin_lat = std::sin(lat_r);
    double cos_lat = std::cos(lat_r);
    double n = WGS84_A / std::sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat);
    double x = (n + alt) * cos_lat * std::cos(lon_r);
    double y = (n + alt) * cos_lat * std::sin(lon_r);
    double z = (n * (1.0 - WGS84_E2) + alt) * sin_lat;
    return ECEF{x, y, z};
}

inline Geodetic ecef_to_geodetic(double x, double y, double z) {
    double lon = std::atan2(y, x);
    double p   = std::hypot(x, y);
    double a   = WGS84_A;
    double b   = a * std::sqrt(1.0 - WGS84_E2);
    double e2  = WGS84_E2;
    double ep2 = (a*a - b*b) / (b*b);
    double th  = std::atan2(a*z, b*p);
    double lat = std::atan2(
        z + ep2*b*std::pow(std::sin(th), 3),
        p - e2*a*std::pow(std::cos(th), 3)
    );
    double sin_lat = std::sin(lat);
    double n = a / std::sqrt(1.0 - e2*sin_lat*sin_lat);
    double alt = p / std::cos(lat) - n;
    return Geodetic{lat * 180.0 / M_PI, lon * 180.0 / M_PI, alt};
}

// ============================================================================
// Camera — matching render/camera.py
// ============================================================================

struct Camera {
    double lat     = 41.9;
    double lon     = 12.5;
    double alt     = 500000.0;
    double yaw     = 0.0;
    double pitch   = -0.3;
    double fov     = M_PI / 3.0;
    double near    = 1000.0;
    double far     = 100000000.0;
    double view_distance = 15000000.0; // eye-to-target distance (meters)
    int    width   = 1024;
    int    height  = 768;

    ECEF ecef_origin() const {
        return geodetic_to_ecef(lat, lon, alt);
    }

    Mat4 view_matrix() const {
        auto e = geodetic_to_ecef(lat, lon, alt);
        Vec3d cx{e.x, e.y, e.z};

        double cy_ = std::cos(yaw);
        double sy_ = std::sin(yaw);
        double cp_ = std::cos(pitch);
        double sp_ = std::sin(pitch);

        Vec3 forward{ static_cast<float>(cy_*cp_), static_cast<float>(sp_), static_cast<float>(sy_*cp_) };
        Vec3 up     { static_cast<float>(-cy_*sp_), static_cast<float>(cp_), static_cast<float>(-sy_*sp_) };

        double px = cx.x + forward.x * view_distance;
        double py = cx.y + forward.y * view_distance;
        double pz = cx.z + forward.z * view_distance;

        Vec3 eye   { static_cast<float>(px - cx.x), static_cast<float>(py - cx.y), static_cast<float>(pz - cx.z) };
        Vec3 target{ 0.0f, 0.0f, 0.0f };

        Vec3 zAxis = (eye - target).normalized();
        Vec3 xAxis = up.cross(zAxis).normalized();
        Vec3 yAxis = zAxis.cross(xAxis);

        Mat4 r = Mat4::identity();
        r.m[0]  = xAxis.x; r.m[1]  = xAxis.y; r.m[2]  = xAxis.z;
        r.m[4]  = yAxis.x; r.m[5]  = yAxis.y; r.m[6]  = yAxis.z;
        r.m[8]  = zAxis.x; r.m[9]  = zAxis.y; r.m[10] = zAxis.z;
        r.m[12] = -xAxis.dot(eye);
        r.m[13] = -yAxis.dot(eye);
        r.m[14] = -zAxis.dot(eye);
        return r;
    }

    Mat4 projection_matrix() const {
        float aspect = static_cast<float>(width) / std::max(height, 1);
        float f  = 1.0f / std::tan(static_cast<float>(fov) * 0.5f);
        float nf = 1.0f / (static_cast<float>(near) - static_cast<float>(far));
        Mat4 r{};
        r.m[0]  = f / aspect;
        r.m[5]  = f;
        r.m[10] = (static_cast<float>(far) + static_cast<float>(near)) * nf;
        r.m[11] = -1.0f;
        r.m[14] = 2.0f * static_cast<float>(far) * static_cast<float>(near) * nf;
        return r;
    }

    Mat4 mvp() const {
        return projection_matrix() * view_matrix();
    }

private:
    double distance_from_surface() const { return view_distance; }
};

// ============================================================================
// Point cloud primitive
// ============================================================================

struct Point3D {
    float  x, y, z;
    uint32_t id;

    Point3D() = default;
    Point3D(float x_, float y_, float z_, uint32_t id_)
        : x(x_), y(y_), z(z_), id(id_) {}
};

// ============================================================================
// Frustum — extracted from VP matrix for per-point culling
// ============================================================================

struct FrustumPlane {
    Vec3  normal;
    float d;

    float distance(const Vec3& p) const { return normal.dot(p) + d; }
};

struct Frustum {
    FrustumPlane planes[6]; // left, right, bottom, top, near, far

    bool contains(const Vec3& p) const {
        for (int i = 0; i < 6; ++i)
            if (planes[i].distance(p) < 0.0f) return false;
        return true;
    }
};

// Extract frustum planes from VP matrix (column-major storage).
// For a world-space point (x,y,z,1), the clip-space coords are:
//   x_clip = m[0]*x + m[4]*y + m[8]*z  + m[12]
//   y_clip = m[1]*x + m[5]*y + m[9]*z  + m[13]
//   z_clip = m[2]*x + m[6]*y + m[10]*z + m[14]
//   w_clip = m[3]*x + m[7]*y + m[11]*z + m[15]
// Frustum half-spaces: x +/- w, y +/- w, z +/- w (with w=1 for world points).
inline Frustum extract_frustum(const Mat4& vp) {
    Frustum f;

    auto plane = [&](float nx, float ny, float nz, float d_) -> FrustumPlane {
        Vec3 n{nx, ny, nz};
        float l = n.length();
        if (l > 1e-8f) { n = n * (1.0f/l); d_ /= l; }
        return { n, d_ };
    };

    f.planes[0] = plane(vp.m[0]+vp.m[3],  vp.m[4]+vp.m[7],  vp.m[8]+vp.m[11],  vp.m[12]+vp.m[15]); // left   (x + w >= 0)
    f.planes[1] = plane(vp.m[3]-vp.m[0],  vp.m[7]-vp.m[4],  vp.m[11]-vp.m[8],  vp.m[15]-vp.m[12]); // right  (x - w >= 0)
    f.planes[2] = plane(vp.m[1]+vp.m[3],  vp.m[5]+vp.m[7],  vp.m[9]+vp.m[11],  vp.m[13]+vp.m[15]); // bottom (y + w >= 0)
    f.planes[3] = plane(vp.m[3]-vp.m[1],  vp.m[7]-vp.m[5],  vp.m[11]-vp.m[9],  vp.m[15]-vp.m[13]); // top    (y - w >= 0)
    f.planes[4] = plane(vp.m[2]+vp.m[3],  vp.m[6]+vp.m[7],  vp.m[10]+vp.m[11], vp.m[14]+vp.m[15]); // near   (z + w >= 0)
    f.planes[5] = plane(vp.m[3]-vp.m[2],  vp.m[7]-vp.m[6],  vp.m[11]-vp.m[10], vp.m[15]-vp.m[14]); // far    (z - w >= 0)

    return f;
}

// ============================================================================
// AABB — axis-aligned bounding box in ECEF space
// ============================================================================

struct AABB {
    Vec3 min_;
    Vec3 max_;

    AABB()
        : min_{+std::numeric_limits<float>::max(), +std::numeric_limits<float>::max(), +std::numeric_limits<float>::max()}
        , max_{-std::numeric_limits<float>::max(), -std::numeric_limits<float>::max(), -std::numeric_limits<float>::max()} {}

    AABB(const Vec3& mn, const Vec3& mx) : min_(mn), max_(mx) {}

    void expand(const Vec3& p) {
        min_.x = std::min(min_.x, p.x); min_.y = std::min(min_.y, p.y); min_.z = std::min(min_.z, p.z);
        max_.x = std::max(max_.x, p.x); max_.y = std::max(max_.y, p.y); max_.z = std::max(max_.z, p.z);
    }

    Vec3 center() const { return (min_ + max_) * 0.5f; }
    Vec3 extent() const { return max_ - min_; }

    bool overlaps(const AABB& o) const {
        return min_.x <= o.max_.x && max_.x >= o.min_.x &&
               min_.y <= o.max_.y && max_.y >= o.min_.y &&
               min_.z <= o.max_.z && max_.z >= o.min_.z;
    }
};

// ============================================================================
// SpatialIndex — 3D uniform grid over a point-cloud bounding box
// ============================================================================
//
// Overview:
//   The point cloud is partitioned into axis-aligned cubic cells of fixed size
//   (in meters, since ECEF is in meters). Each cell stores the indices of the
//   points that fall inside it.
//
//   This is the simplest spatial acceleration structure. For Earth-scale data
//   one would use a cube-quadtree (matching AetherMap's cube-sphere faces),
//   but the uniform grid is sufficient for a local point cloud and is the
//   natural building block for Milestone 6.
//
//   Future integration with Milestone 5 LOD:
//     Only points returned by query_frustum() are submitted to the LOD selector,
//     dramatically reducing the per-frame candidate set.

class SpatialIndex {
public:
    struct CellKey {
        int x, y, z;

        bool operator==(const CellKey& o) const { return x == o.x && y == o.y && z == o.z; }
    };

    struct CellKeyHash {
        std::size_t operator()(const CellKey& k) const noexcept {
            std::size_t hx = static_cast<std::size_t>(k.x) * 73856093u;
            std::size_t hy = static_cast<std::size_t>(k.y) * 19349663u;
            std::size_t hz = static_cast<std::size_t>(k.z) * 83492791u;
            return hx ^ hy ^ hz;
        }
    };

    SpatialIndex() = default;

    SpatialIndex(const AABB& bounds, float cell_size)
        : min_corner_(bounds.min_)
        , cell_size_(cell_size > 0.0f ? cell_size : 1.0f)
        , inv_cell_size_(1.0f / cell_size_)
    {}

    template <typename It>
    SpatialIndex(It begin, It end, float cell_size)
        : cell_size_(cell_size > 0.0f ? cell_size : 1.0f)
        , inv_cell_size_(1.0f / cell_size_)
    {
        for (auto it = begin; it != end; ++it)
            bounds_.expand(Vec3(it->x, it->y, it->z));
        min_corner_ = bounds_.min_;
        // Actually insert points into cells after computing bounds
        for (auto it = begin; it != end; ++it)
            insert(*it);
    }

    void insert(const Point3D& point) {
        CellKey key = world_to_cell(Vec3(point.x, point.y, point.z));
        cells_[key].push_back(point.id);
        point_count_++;
        bounds_.expand(Vec3(point.x, point.y, point.z));
    }

    void insert(const std::vector<Point3D>& points) {
        for (const auto& p : points) insert(p);
    }

    void clear() {
        cells_.clear();
        point_count_ = 0;
        bounds_ = AABB{};
    }

    std::vector<uint32_t> query_aabb(const AABB& query) const {
        std::vector<uint32_t> result;
        result.reserve(64);

        CellKey min_cell = aabb_to_cell(query.min_);
        CellKey max_cell = aabb_to_cell(query.max_);

        for (int cx = min_cell.x; cx <= max_cell.x; ++cx)
            for (int cy = min_cell.y; cy <= max_cell.y; ++cy)
                for (int cz = min_cell.z; cz <= max_cell.z; ++cz) {
                    CellKey key{cx, cy, cz};
                    auto it = cells_.find(key);
                    if (it != cells_.end())
                        result.insert(result.end(), it->second.begin(), it->second.end());
                }
        return result;
    }

    std::vector<uint32_t> query_frustum(const Camera& camera,
                                        const std::vector<Point3D>& points,
                                        bool precise = true) const {
        AABB frustum_aabb = compute_frustum_aabb(camera);
        std::vector<uint32_t> candidates = query_aabb(frustum_aabb);

        if (!precise || candidates.empty())
            return candidates;

        Frustum frustum = extract_frustum(camera.mvp());

        auto cam_ecef = camera.ecef_origin();
        Vec3 cam_pos{ static_cast<float>(cam_ecef.x),
                      static_cast<float>(cam_ecef.y),
                      static_cast<float>(cam_ecef.z) };

        std::vector<uint32_t> visible;
        visible.reserve(candidates.size());

        for (uint32_t idx : candidates) {
            if (idx >= points.size()) continue;
            const Point3D& pt = points[idx];
            Vec3 p{pt.x, pt.y, pt.z};

            Vec3 d = p - cam_pos;
            float dist = d.length();
            if (dist < static_cast<float>(camera.near) || dist > static_cast<float>(camera.far))
                continue;

            if (frustum.contains(p))
                visible.push_back(idx);
        }
        return visible;
    }

    size_t point_count()  const { return point_count_; }
    size_t cell_count()   const { return cells_.size(); }
    float  cell_size()    const { return cell_size_; }
    AABB   bounds()       const { return bounds_; }

private:
    CellKey world_to_cell(const Vec3& p) const {
        return {
            static_cast<int>((p.x - min_corner_.x) * inv_cell_size_),
            static_cast<int>((p.y - min_corner_.y) * inv_cell_size_),
            static_cast<int>((p.z - min_corner_.z) * inv_cell_size_)
        };
    }

    CellKey aabb_to_cell(const Vec3& p) const {
        return {
            static_cast<int>((p.x - min_corner_.x) * inv_cell_size_),
            static_cast<int>((p.y - min_corner_.y) * inv_cell_size_),
            static_cast<int>((p.z - min_corner_.z) * inv_cell_size_)
        };
    }

    static AABB compute_frustum_aabb(const Camera& camera) {
        Mat4 vp = camera.mvp();
        Mat4 inv = vp.inverse();
        if (inv == Mat4::identity()) {
            auto e = camera.ecef_origin();
            Vec3 o{ static_cast<float>(e.x), static_cast<float>(e.y), static_cast<float>(e.z) };
            return AABB{ o - Vec3{50000,50000,50000}, o + Vec3{50000,50000,50000} };
        }

        AABB aabb;
        const float corners[8][4] = {
            {-1,-1,-1, 1}, {+1,-1,-1, 1}, {-1,+1,-1, 1}, {+1,+1,-1, 1},
            {-1,-1,+1, 1}, {+1,-1,+1, 1}, {-1,+1,+1, 1}, {+1,+1,+1, 1}
        };
        for (int i = 0; i < 8; ++i) {
            Vec3 p = inv.transform_point(Vec3{corners[i][0], corners[i][1], corners[i][2]});
            aabb.expand(p);
        }
        return aabb;
    }

    Vec3  min_corner_{0.0f, 0.0f, 0.0f};
    float cell_size_{100000.0f};
    float inv_cell_size_{1.0e-5f};
    size_t point_count_{0};
    AABB  bounds_;

    std::unordered_map<CellKey, std::vector<uint32_t>, CellKeyHash> cells_;
};

} // namespace aethermap
