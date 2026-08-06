"""AetherMap Fase 2 — Geo data loader from OpenStreetMap.

Optional dependencies:
    pip install aethermap[geo]

Exposes:
    load_roads(place_name, network_type) -> GeoJSON FeatureCollection
    load_cities(bbox, tags) -> GeoJSON FeatureCollection
    load_peaks(bbox, min_ele) -> GeoJSON FeatureCollection
    to_digital_twin(fc) -> list[Oggetto]
    simplify_geojson(fc, tolerance) -> GeoJSON FeatureCollection
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_OSMNX_AVAILABLE = False
try:
    import osmnx as ox  # type: ignore[import-untyped]
    from osmnx import geocoder  # type: ignore[import-untyped]

    _OSMNX_AVAILABLE = True
except ImportError:
    ox = None  # type: ignore[assignment]
    geocoder = None  # type: ignore[assignment]

_GPD_AVAILABLE = False
try:
    import geopandas as gpd  # type: ignore[import-untyped]
    from shapely.geometry import LineString, Point  # type: ignore[import-untyped]

    _GPD_AVAILABLE = True
except ImportError:
    gpd = None  # type: ignore[assignment]
    LineString = None  # type: ignore[assignment,misc]
    Point = None  # type: ignore[assignment,misc]


class GeoDependenciesMissing(RuntimeError):
    """Raised when optional geo dependencies are not installed."""


def _require_deps() -> None:
    if not _OSMNX_AVAILABLE or not _GPD_AVAILABLE:
        raise GeoDependenciesMissing(
            "Geo dependencies missing. Install with: pip install aethermap[geo]"
        )


def load_roads(
    place_name: str,
    network_type: str = "drive",
    simplify: bool = True,
) -> dict[str, Any]:
    """Load road network from OpenStreetMap for a place name.

    Args:
        place_name: OSM place query (e.g. "Pavia, Italy").
        network_type: osmnx network type (drive, walk, bike, all).
        simplify: simplify geometries with shapely.

    Returns:
        GeoJSON FeatureCollection with LineString features.
    """
    _require_deps()
    ox.settings.use_cache = True
    ox.settings.log_console = False
    G = ox.graph_from_place(place_name, network_type=network_type)
    edges = ox.graph_to_gdfs(G, nodes=False)
    if simplify:
        edges["geometry"] = edges["geometry"].simplify(tolerance=0.0005, preserve_topology=True)
    gj = edges.__geo_interface__
    return _normalize_geojson(gj, default_type="strada")


def load_cities(
    bbox: tuple[float, float, float, float],
    tags: dict[str, list[str]] | None = None,
    simplify: bool = True,
) -> dict[str, Any]:
    """Load city/place POIs within a bounding box.

    Args:
        bbox: (north, south, east, west) in WGS84.
        tags: OSM tags filter. Default: place=city,town,village.
        simplify: simplify point geometries (no-op for points).

    Returns:
        GeoJSON FeatureCollection with Point features.
    """
    _require_deps()
    if tags is None:
        tags = {"place": ["city", "town", "village", "hamlet"]}
    north, south, east, west = bbox
    features = []
    for _, values in tags.items():
        for value in values:
            try:
                pois = geocoder.geocode_to_gdf(
                    f"{value} [{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}]"
                )
            except Exception:
                continue
            if pois is None or pois.empty:
                continue
            for _, row in pois.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": row.get("display_name", "").split(",")[0],
                        "place": value,
                        "type": "citta",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [geom.x, geom.y],
                    },
                })
    return {"type": "FeatureCollection", "features": features}


def load_peaks(
    bbox: tuple[float, float, float, float],
    min_ele: float = 0.0,
) -> dict[str, Any]:
    """Load mountain peaks within a bounding box.

    Args:
        bbox: (north, south, east, west).
        min_ele: minimum elevation in meters.

    Returns:
        GeoJSON FeatureCollection with Point features.
    """
    _require_deps()
    tags = {"natural": "peak", "ele": True}
    north, south, east, west = bbox
    try:
        gdf = ox.geometries_from_bbox(north, south, east, west, tags=tags)
    except Exception:
        return {"type": "FeatureCollection", "features": []}
    features = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if hasattr(geom, "x") and hasattr(geom, "y") or geom.geom_type == "Point":
            coords = [geom.x, geom.y]
        else:
            continue
        ele = row.get("ele")
        try:
            ele_f = float(ele) if ele is not None else None
        except (TypeError, ValueError):
            ele_f = None
        if ele_f is not None and ele_f < min_ele:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "name": row.get("name", ""),
                "ele": ele_f,
                "type": "montagna",
            },
            "geometry": {
                "type": "Point",
                "coordinates": coords,
            },
        })
    return {"type": "FeatureCollection", "features": features}


def simplify_geojson(
    fc: dict[str, Any],
    tolerance: float = 0.0005,
) -> dict[str, Any]:
    """Simplify geometries in a GeoJSON FeatureCollection.

    Args:
        fc: GeoJSON FeatureCollection.
        tolerance: simplification tolerance in degrees.

    Returns:
        Simplified GeoJSON FeatureCollection.
    """
    if not _GPD_AVAILABLE:
        return fc
    try:
        gdf = gpd.GeoDataFrame.from_features(fc["features"])
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=tolerance, preserve_topology=True)
        return gdf.__geo_interface__
    except Exception:
        return fc


def to_digital_twin(fc: dict[str, Any]) -> list[Any]:
    """Convert a GeoJSON FeatureCollection to AetherMap DigitalTwin objects.

    Imports aethermap.ai.models lazily to avoid circular imports.

    Returns:
        List of Oggetto instances.
    """
    try:
        from aethermap.ai.models import (  # type: ignore[import]
            Geometria,  # noqa: F401  # imported for availability
            Oggetto,
            Posizione,
        )
    except ImportError as exc:
        raise RuntimeError(
            "aethermap package is required for digital twin conversion"
        ) from exc

    objects: list[Any] = []
    for idx, feature in enumerate(fc.get("features", [])):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])
        tipo = props.get("type", "sconosciuto")
        name = props.get("name", f"{tipo}-{idx}")
        obj_id = name.replace(" ", "_").lower()

        if tipo == "strada" and geom_type == "LineString":
            punti = []
            for coord in coords:
                if len(coord) >= 2:
                    punti.append({"lat": coord[1], "lon": coord[0], "ele": coord[2] if len(coord) > 2 else 0.0})
            if not punti:
                continue
            try:
                from aethermap.twin.objects import make_strada  # type: ignore[import]
                obj = make_strada(obj_id, punti[0]["lat"], punti[0]["lon"], punti)
                objects.append(obj)
            except Exception:
                pos = Posizione.from_latlon(punti[0]["lat"], punti[0]["lon"])
                geom_data = Geometria(tipo="linea", dati={"punti": punti})
                obj = Oggetto(id=obj_id, tipo=tipo, posizione=pos, geometria=geom_data, proprieta={"name": name})
                objects.append(obj)

        elif tipo in ("montagna", "peak") and geom_type == "Point" and len(coords) >= 2:
            lat, lon = coords[1], coords[0]
            ele = props.get("ele") or 0.0
            try:
                ele_f = float(ele)
            except (TypeError, ValueError):
                ele_f = 0.0
            try:
                from aethermap.twin.objects import make_montagna  # type: ignore[import]
                obj = make_montagna(obj_id, lat, lon, ele_f, [])
                objects.append(obj)
            except Exception:
                pos = Posizione.from_latlon(lat, lon, alt=ele_f)
                obj = Oggetto(id=obj_id, tipo="montagna", posizione=pos, proprieta={"name": name, "ele": ele_f})
                objects.append(obj)

        elif tipo in ("citta", "city", "town", "village") and geom_type == "Point" and len(coords) >= 2:
            lat, lon = coords[1], coords[0]
            pos = Posizione.from_latlon(lat, lon)
            obj = Oggetto(
                id=obj_id,
                tipo="citta",
                posizione=pos,
                proprieta={"name": name, "place": props.get("place", "")},
            )
            objects.append(obj)

    return objects


def _normalize_geojson(gj: dict[str, Any], default_type: str = "feature") -> dict[str, Any]:
    if gj.get("type") == "FeatureCollection":
        return gj
    if gj.get("type") == "Feature":
        return {"type": "FeatureCollection", "features": [gj]}
    return {"type": "FeatureCollection", "features": []}
