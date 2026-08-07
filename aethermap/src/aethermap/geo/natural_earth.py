"""AetherMap — Natural Earth data loader.

Downloads and parses public-domain vector data from Natural Earth:
- Coastlines (LineStrings)
- Country borders (LineStrings)
- Populated places / cities (Points)

Data source: https://github.com/nvkelso/natural-earth-vector
License: public domain (CC0)

Optional dependencies:
    pip install aethermap[geo]
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_NE_BASE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
)
_NE_CACHE_DIR = Path(__file__).resolve().parent / "natural_earth"
_NE_CACHE_DIR.mkdir(exist_ok=True)

_COASTLINE_FILE = "ne_10m_coastline.geojson"
_BORDERS_FILE = "ne_10m_admin_0_boundary_lines_land.geojson"
_CITIES_FILE = "ne_10m_populated_places_simple.geojson"

_GPD_AVAILABLE = False
try:
    import geopandas as gpd  # type: ignore[import-untyped]

    _GPD_AVAILABLE = True
except ImportError:
    gpd = None  # type: ignore[assignment]


def _download(url: str, dest: Path) -> None:
    """Download a file if not already cached."""
    if dest.exists() and dest.stat().st_size > 0:
        return
    try:
        import requests

        logger.info("[natural_earth] downloading %s -> %s", url, dest)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        logger.info("[natural_earth] saved %d bytes to %s", len(resp.content), dest)
    except Exception as exc:
        logger.warning("[natural_earth] download failed: %s", exc)
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise


def _geojson_url(filename: str) -> str:
    return f"{_NE_BASE_URL}/{filename}"


def _local_path(filename: str) -> Path:
    return _NE_CACHE_DIR / filename


def load_coastlines(
    resolution: str = "110m",
    simplify: bool = True,
    tolerance: float = 0.005,
) -> dict[str, Any]:
    """Load Natural Earth coastline data.

    Args:
        resolution: data resolution ('10m', '50m', '110m').
        simplify: simplify geometries to reduce vertex count.
        tolerance: simplification tolerance in degrees.

    Returns:
        GeoJSON FeatureCollection with LineString features.
    """
    filename = f"ne_{resolution}_coastline.geojson"
    path = _local_path(filename)
    url = _geojson_url(filename)
    _download(url, path)
    gj = json.loads(path.read_text(encoding="utf-8"))
    if simplify and _GPD_AVAILABLE:
        gj = _simplify_geojson(gj, tolerance)
    return gj


def load_country_borders(
    resolution: str = "110m",
    simplify: bool = True,
    tolerance: float = 0.005,
) -> dict[str, Any]:
    """Load Natural Earth land borders data.

    Args:
        resolution: data resolution ('10m', '50m', '110m').
        simplify: simplify geometries.
        tolerance: simplification tolerance in degrees.

    Returns:
        GeoJSON FeatureCollection with LineString features.
    """
    filename = f"ne_{resolution}_admin_0_boundary_lines_land.geojson"
    path = _local_path(filename)
    url = _geojson_url(filename)
    _download(url, path)
    gj = json.loads(path.read_text(encoding="utf-8"))
    if simplify and _GPD_AVAILABLE:
        gj = _simplify_geojson(gj, tolerance)
    return gj


def load_cities(
    resolution: str = "110m",
    min_pop: int = 50000,
    simplify: bool = True,
    tolerance: float = 0.0005,
) -> dict[str, Any]:
    """Load Natural Earth populated places.

    Natural Earth only provides populated places data at the 10m resolution.
    The ``resolution`` parameter is accepted for API consistency but is
    ignored; the data is always fetched from ``ne_10m_populated_places_simple.geojson``.
    The ``min_pop`` filter controls which cities are returned, effectively
    providing coarser results for larger requested resolutions.

    Args:
        resolution: data resolution (ignored, kept for API compat).
        min_pop: minimum population filter.
        simplify: simplify geometries (no-op for points).
        tolerance: simplification tolerance in degrees.

    Returns:
        GeoJSON FeatureCollection with Point features.
    """
    filename = "ne_10m_populated_places_simple.geojson"
    path = _local_path(filename)
    url = _geojson_url(filename)
    _download(url, path)
    gj = json.loads(path.read_text(encoding="utf-8"))

    features = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        pop = props.get("pop_max") or props.get("pop_min") or 0
        try:
            pop_val = int(pop)
        except (TypeError, ValueError):
            pop_val = 0
        if pop_val < min_pop:
            continue
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom.get("type") != "Point" or len(coords) < 2:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "name": props.get("name", ""),
                "pop": pop_val,
                "type": "citta",
            },
            "geometry": {
                "type": "Point",
                "coordinates": coords,
            },
        })

    result = {"type": "FeatureCollection", "features": features}
    if simplify and _GPD_AVAILABLE:
        result = _simplify_geojson(result, tolerance)
    return result


def load_land_polygons(
    resolution: str = "10m",
    simplify: bool = True,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Load Natural Earth land polygons.

    Args:
        resolution: data resolution ('10m', '50m', '110m').
        simplify: simplify geometries.
        tolerance: simplification tolerance in degrees.

    Returns:
        GeoJSON FeatureCollection with Polygon/MultiPolygon features.
    """
    filename = f"ne_{resolution}_land.geojson"
    path = _local_path(filename)
    url = _geojson_url(filename)
    _download(url, path)
    gj = json.loads(path.read_text(encoding="utf-8"))
    if simplify and _GPD_AVAILABLE:
        gj = _simplify_geojson(gj, tolerance)
    return gj


def _simplify_geojson(
    gj: dict[str, Any],
    tolerance: float = 0.0005,
) -> dict[str, Any]:
    if not _GPD_AVAILABLE:
        return gj
    try:
        gdf = gpd.GeoDataFrame.from_features(gj["features"])
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=tolerance, preserve_topology=True)
        return gdf.__geo_interface__
    except Exception:
        return gj


def to_entities(
    coastlines: dict[str, Any] | None = None,
    borders: dict[str, Any] | None = None,
    cities: dict[str, Any] | None = None,
    merge_lines: bool = True,
    max_line_vertices: int = 2000,
) -> dict[str, Any]:
    """Convert Natural Earth data to AetherMap entity format.

    Args:
        coastlines: GeoJSON coastline FeatureCollection.
        borders: GeoJSON border FeatureCollection.
        cities: GeoJSON cities FeatureCollection.
        merge_lines: merge consecutive line segments into longer lines.
        max_line_vertices: max vertices per merged line segment.

    Returns:
        Dict with entities list and statistics.
    """

    entities: list[dict[str, Any]] = []

    def _add_coastline(coords: list[list[float]], seg_idx: int) -> None:
        if len(coords) < 2:
            return
        if merge_lines:
            chunks = []
            for i in range(0, len(coords), max_line_vertices):
                chunk = coords[i:i + max_line_vertices]
                if len(chunk) >= 2:
                    chunks.append(chunk)
            for ci, chunk in enumerate(chunks):
                pts = [{"lat": c[1], "lon": c[0], "ele": 0.0} for c in chunk if len(c) >= 2]
                if len(pts) < 2:
                    continue
                entities.append({
                    "id": f"coastline_{seg_idx}_{ci}",
                    "tipo": "costa",
                    "color": [0.15, 0.55, 0.95],
                    "kind": "line",
                    "points": pts,
                    "props": {"source": "natural_earth", "type": "coastline"},
                    "confidence": 1.0,
                })
        else:
            pts = [{"lat": c[1], "lon": c[0], "ele": 0.0} for c in coords if len(c) >= 2]
            if len(pts) >= 2:
                entities.append({
                    "id": f"coastline_{seg_idx}",
                    "tipo": "costa",
                    "color": [0.15, 0.55, 0.95],
                    "kind": "line",
                    "points": pts,
                    "props": {"source": "natural_earth", "type": "coastline"},
                    "confidence": 1.0,
                })

    def _add_border(coords: list[list[float]], seg_idx: int) -> None:
        if len(coords) < 2:
            return
        pts = [{"lat": c[1], "lon": c[0], "ele": 0.0} for c in coords if len(c) >= 2]
        if len(pts) < 2:
            return
        entities.append({
            "id": f"border_{seg_idx}",
            "tipo": "confine",
            "color": [0.6, 0.55, 0.5],
            "kind": "line",
            "points": pts,
            "props": {"source": "natural_earth", "type": "border"},
            "confidence": 0.9,
        })

    def _add_city(coords: list[float], props: dict[str, Any], idx: int) -> None:
        if len(coords) < 2:
            return
        pop = props.get("pop", 0)
        try:
            pop_val = int(pop)
        except (TypeError, ValueError):
            pop_val = 0
        entities.append({
            "id": f"city_{idx}",
            "tipo": "citta",
            "color": [1.0, 0.95, 0.8],
            "kind": "point",
            "position": [coords[1], coords[0]],
            "props": {
                "source": "natural_earth",
                "type": "city",
                "name": props.get("name", ""),
                "pop": pop_val,
            },
            "confidence": 0.95,
        })

    if coastlines:
        for idx, feat in enumerate(coastlines.get("features", [])):
            geom = feat.get("geometry", {})
            gtype = geom.get("type", "")
            if gtype == "LineString":
                _add_coastline(geom.get("coordinates", []), idx)
            elif gtype == "MultiLineString":
                for mi, line in enumerate(geom.get("coordinates", [])):
                    _add_coastline(line, f"{idx}_{mi}")

    if borders:
        for idx, feat in enumerate(borders.get("features", [])):
            geom = feat.get("geometry", {})
            gtype = geom.get("type", "")
            if gtype == "LineString":
                _add_border(geom.get("coordinates", []), idx)
            elif gtype == "MultiLineString":
                for mi, line in enumerate(geom.get("coordinates", [])):
                    _add_border(line, f"{idx}_{mi}")

    if cities:
        for idx, feat in enumerate(cities.get("features", [])):
            geom = feat.get("geometry", {})
            if geom.get("type") != "Point":
                continue
            _add_city(geom.get("coordinates", []), feat.get("properties", {}), idx)

    coastline_count = len([e for e in entities if e["tipo"] == "costa"])
    border_count = len([e for e in entities if e["tipo"] == "confine"])
    city_count = len([e for e in entities if e["tipo"] == "citta"])

    return {
        "entities": entities,
        "coastline_count": coastline_count,
        "border_count": border_count,
        "city_count": city_count,
    }
