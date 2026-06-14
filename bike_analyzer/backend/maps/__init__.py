"""Maps package."""

from typing import Any

_MAP_ATTRS = {
    "create_route_map": ("map_renderer", "create_route_map"),
    "get_local_results": ("osm_maps", "get_local_results"),
    "search_nearby": ("osm_maps", "search_nearby"),
    "search_places": ("osm_maps", "search_places"),
}


def __getattr__(name: str) -> Any:
    if name not in _MAP_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _MAP_ATTRS[name]
    module = __import__(f"bike_analyzer.backend.maps.{module_name}", fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = sorted(_MAP_ATTRS)
