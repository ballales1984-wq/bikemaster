"""Maps package."""

from __future__ import annotations

import importlib
import os
from typing import Any

_MAP_ATTRS: dict[str, tuple[str, str]] = {
    "create_route_map": ("map_renderer", "create_route_map"),
    "get_local_results": ("osm_maps", "get_local_results"),
    "search_nearby": ("osm_maps", "search_nearby"),
    "search_places": ("osm_maps", "search_places"),
}

_AETHERMAP_ATTRS: dict[str, tuple[str, str]] = {
    "create_route_map_aethermap": ("aethermap_adapter", "create_route_map"),
}


def _get_map_provider() -> str:
    return os.getenv("BIKEMASTER_MAP_PROVIDER", "folium").lower()


def __getattr__(name: str) -> Any:
    if name in _AETHERMAP_ATTRS:
        module_name, attr_name = _AETHERMAP_ATTRS[name]
        module = importlib.import_module(f"bike_analyzer.backend.maps.{module_name}")
        return getattr(module, attr_name)

    if name not in _MAP_ATTRS:
        raise AttributeError(name)

    if name == "create_route_map" and _get_map_provider() == "aethermap":
        try:
            module = importlib.import_module("bike_analyzer.backend.maps.aethermap_adapter")
            return module.create_route_map
        except ImportError:
            pass

    module_name, attr_name = _MAP_ATTRS[name]
    module = importlib.import_module(f"bike_analyzer.backend.maps.{module_name}")
    return getattr(module, attr_name)


__all__ = sorted(_MAP_ATTRS | _AETHERMAP_ATTRS)
