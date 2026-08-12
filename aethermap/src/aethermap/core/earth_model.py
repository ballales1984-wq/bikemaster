"""Earth model for AetherMap (Phase 1).

Provides the mathematical model of the Earth as described in Phase 1 §1.6:
a parametric surface + a heightfield ``F(λ, φ, t)``.

Components:
    - WGS84 ellipsoid parameters
    - Ellipsoid geometry (radius, area, curvature)
    - Geoid model interface (EGM96/2008 stub)
    - Heightfield abstraction
    - Simple gravity model
    - Time-aware field interface
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Optional

from aethermap.core.coordinates import (
    EARTH_RADIUS_MEAN,
    WGS84_A,
    WGS84_B,
    WGS84_E2,
    WGS84_F,
    Geodetic,
)

# ---------------------------------------------------------------------------
# Earth parameters
# ---------------------------------------------------------------------------

EARTH_RADIUS_VOLUMETRIC = 6_371_000.8  # volumetric mean radius (IAU 2015)
EARTH_RADIUS_AUTHALIC = 6_371_007.2   # authalic radius (equal-area sphere)


@dataclass(frozen=True)
class EarthParams:
    """WGS84 ellipsoid parameters and derived constants."""

    semi_major_axis: float = WGS84_A       # a (equatorial) in meters
    semi_minor_axis: float = WGS84_B       # b (polar) in meters
    flattening: float = WGS84_F           # f = (a-b)/a
    eccentricity_squared: float = WGS84_E2  # e² = f(2-f)
    mean_radius: float = EARTH_RADIUS_MEAN
    volumetric_radius: float = EARTH_RADIUS_VOLUMETRIC
    authalic_radius: float = EARTH_RADIUS_AUTHALIC

    def radius_of_curvature(self, lat: float) -> float:
        """Prime vertical radius of curvature at geodetic latitude (meters)."""
        lat_r = math.radians(lat)
        sin_lat = math.sin(lat_r)
        return self.semi_major_axis / math.sqrt(
            1.0 - self.eccentricity_squared * sin_lat * sin_lat
        )

    def surface_radius(self, lat: float) -> float:
        """Distance from Earth center to ellipsoid surface at geodetic latitude."""
        lat_r = math.radians(lat)
        sin_lat = math.sin(lat_r)
        cos_lat = math.cos(lat_r)
        n = self.radius_of_curvature(lat)
        return math.sqrt((n * cos_lat) ** 2 + (n * (1.0 - self.eccentricity_squared) * sin_lat) ** 2)

    def surface_area(self) -> float:
        """Total surface area of the ellipsoid (m²)."""
        a, b = self.semi_major_axis, self.semi_minor_axis
        e2 = self.eccentricity_squared
        e = math.sqrt(e2)
        return 2.0 * math.pi * a**2 * (1.0 + (1.0 - e2) / e * math.atanh(e))

    def meridian_arc_length(self, lat1: float, lat2: float) -> float:
        """Length of meridian arc between two geodetic latitudes (meters)."""
        a, b = self.semi_major_axis, self.semi_minor_axis
        e2 = self.eccentricity_squared
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        m = lambda lat_r: a * (1.0 - e2) / (1.0 - e2 * math.sin(lat_r) ** 2) ** 1.5
        steps = 1000
        total = 0.0
        for i in range(steps):
            phi1 = lat1_r + (lat2_r - lat1_r) * i / steps
            phi2 = lat1_r + (lat2_r - lat1_r) * (i + 1) / steps
            total += 0.5 * (m(phi1) + m(phi2)) * abs(phi2 - phi1)
        return total


EARTH = EarthParams()


# ---------------------------------------------------------------------------
# Geoid model
# ---------------------------------------------------------------------------

class GeoidModel(ABC):
    """Abstract geoid model for orthometric height conversion."""

    @abstractmethod
    def height(self, lat: float, lon: float) -> float:
        """Geoid height above the ellipsoid at (lat, lon) in meters."""
        ...


class EGM96Geoid(GeoidModel):
    """EGM96 geoid model (simplified stub).

    The full EGM96 model requires a 3601×1801 grid of spherical harmonic
    coefficients. For Phase 1, this stub returns 0 (no geoid correction).
    A full implementation would load the coefficients and evaluate the
    spherical harmonic series.
    """

    def height(self, lat: float, lon: float) -> float:
        return 0.0


class EGM2008Geoid(GeoidModel):
    """EGM2008 geoid model (simplified stub).

    Similar to EGM96 but with higher resolution (2191×2161 coefficients).
    Phase 1 stub returns 0.
    """

    def height(self, lat: float, lon: float) -> float:
        return 0.0


# Global geoid instance (configurable)
_geoid: GeoidModel = EGM96Geoid()


def set_geoid(model: GeoidModel) -> None:
    """Set the active geoid model for orthometric height calculations."""
    global _geoid
    _geoid = model


def geoid_height(lat: float, lon: float) -> float:
    """Current geoid height at (lat, lon) in meters (above ellipsoid)."""
    return _geoid.height(lat, lon)


# ---------------------------------------------------------------------------
# Heightfield abstraction F(λ, φ, t)
# ---------------------------------------------------------------------------

@dataclass
class HeightSample:
    """A single sample of the heightfield F(λ, φ, t)."""

    lat: float
    lon: float
    elevation_m: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 1.0
    source: str = "unknown"


class Heightfield(ABC):
    """Abstract heightfield F(λ, φ, t) for the Earth model.

    This is the "skin" of the planet: a continuously sampled field of
    elevation (and potentially other scalar fields like temperature,
    traffic density, etc.) parameterized by geodetic coordinates and time.
    """

    @abstractmethod
    def sample(self, lat: float, lon: float, t: Optional[datetime] = None) -> float:
        """Return elevation at (lat, lon) at time t (meters above ellipsoid)."""
        ...

    @abstractmethod
    def sample_batch(
        self, points: list[tuple[float, float]], t: Optional[datetime] = None
    ) -> list[float]:
        """Batch version for performance."""
        ...

    @abstractmethod
    def gradient(
        self, lat: float, lon: float, t: Optional[datetime] = None
    ) -> tuple[float, float]:
        """Return (dF/dλ, dF/dφ) — gradient for slope/normal calculations."""
        ...


class ProceduralHeightfield(Heightfield):
    """Procedural heightfield using fractal Brownian motion (fBM).

    Used for demo/placeholder terrain. Not geographically accurate.
    """

    def __init__(
        self,
        seed: int = 42,
        octaves: int = 6,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        scale: float = 0.01,
        amplitude: float = 2000.0,
    ) -> None:
        self.seed = seed
        self.octaves = octaves
        self.persistence = persistence
        self.lacunarity = lacunarity
        self.scale = scale
        self.amplitude = amplitude
        self._rng = _seed_rng(seed)

    def sample(self, lat: float, lon: float, t: Optional[datetime] = None) -> float:
        return self._fbm(lat, lon) * self.amplitude

    def sample_batch(
        self, points: list[tuple[float, float]], t: Optional[datetime] = None
    ) -> list[float]:
        return [self.sample(lat, lon, t) for lat, lon in points]

    def gradient(
        self, lat: float, lon: float, t: Optional[datetime] = None
    ) -> tuple[float, float]:
        eps = 0.0001
        df_dlat = (self._fbm(lat + eps, lon) - self._fbm(lat - eps, lon)) / (2.0 * eps)
        df_dlon = (self._fbm(lat, lon + eps) - self._fbm(lat, lon - eps)) / (2.0 * eps)
        return df_dlat * self.amplitude, df_dlon * self.amplitude

    def _fbm(self, lat: float, lon: float) -> float:
        value = 0.0
        amp = 1.0
        freq = self.scale
        for _ in range(self.octaves):
            value += amp * _noise2d(lat * freq, lon * freq, self._rng)
            freq *= self.lacunarity
            amp *= self.persistence
        return value


class CompositeHeightfield(Heightfield):
    """Heightfield composed of multiple layers (DEM + procedural + features)."""

    def __init__(self, layers: list[tuple[Heightfield, float]]) -> None:
        """Initialize with (heightfield, weight) tuples."""
        self.layers = layers

    def sample(self, lat: float, lon: float, t: Optional[datetime] = None) -> float:
        return sum(hf.sample(lat, lon, t) * w for hf, w in self.layers)

    def sample_batch(
        self, points: list[tuple[float, float]], t: Optional[datetime] = None
    ) -> list[float]:
        return [self.sample(lat, lon, t) for lat, lon in points]

    def gradient(
        self, lat: float, lon: float, t: Optional[datetime] = None
    ) -> tuple[float, float]:
        gx, gy = 0.0, 0.0
        for hf, w in self.layers:
            gxi, gyi = hf.gradient(lat, lon, t)
            gx += gxi * w
            gy += gyi * w
        return gx, gy


# ---------------------------------------------------------------------------
# Gravity model
# ---------------------------------------------------------------------------

def gravity_wgs84(lat: float, alt: float = 0.0) -> float:
    """WGS84 ellipsoid gravity (m/s²) at geodetic latitude and altitude.

    Uses the Somigliana formula on the ellipsoid, with free-air correction.
    """
    lat_r = math.radians(lat)
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)

    # Somigliana formula
    e2 = WGS84_E2
    k = 0.00193185265241  # WGS84 constant
    gamma_e = 9.7803253359  # equatorial gravity (m/s²)
    gamma_p = 9.8321849378  # polar gravity (m/s²)

    gamma = (
        gamma_e * cos_lat**2 + gamma_p * sin_lat**2
    ) / math.sqrt(cos_lat**2 + (1.0 - e2) * sin_lat**2)
    gamma *= 1.0 + k * sin_lat**2

    # Free-air correction: ~0.3086 mGal/m = 3.086e-6 s⁻²
    gamma -= 3.086e-6 * alt

    return gamma


# ---------------------------------------------------------------------------
# Utility: simple PRNG for procedural generation
# ---------------------------------------------------------------------------

def _seed_rng(seed: int) -> "_Random":
    """Simple linear congruential generator for procedural noise."""
    state = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return state / 0xFFFFFFFF

    return rng


def _noise2d(x: float, y: float, rng: Callable[[], float]) -> float:
    """Value noise: hash grid corners and interpolate."""
    xi = math.floor(x)
    yi = math.floor(y)
    xf = x - xi
    yf = y - yi
    # Smoothstep
    u = xf * xf * (3.0 - 2.0 * xf)
    v = yf * yf * (3.0 - 2.0 * yf)
    # Hash corners using rng for seed-dependent values
    a = _hash(xi, yi) ^ int(rng() * 65536)
    b = _hash(xi + 1, yi) ^ int(rng() * 65536)
    c = _hash(xi, yi + 1) ^ int(rng() * 65536)
    d = _hash(xi + 1, yi + 1) ^ int(rng() * 65536)
    # Normalize to [0, 1]
    a, b, c, d = a / 65536.0, b / 65536.0, c / 65536.0, d / 65536.0
    return a * (1.0 - u) * (1.0 - v) + b * u * (1.0 - v) + c * (1.0 - u) * v + d * u * v


def _hash(x: int, y: int) -> int:
    """Deterministic hash for integer grid coordinates."""
    n = x * 374761393 + y * 668265263
    n = (n ^ (n >> 13)) & 0xFFFFFFFF
    for _ in range(3):
        n = (1664525 * n + 1013904223) & 0xFFFFFFFF
    return n & 0xFFFF
