"""Database package."""

from typing import Any

_DB_ATTRS = {
    "delete_ride": ("database", "delete_ride"),
    "get_all_rides": ("database", "get_all_rides"),
    "get_ride": ("database", "get_ride"),
    "init_db": ("database", "init_db"),
    "save_ride": ("database", "save_ride"),
}


def __getattr__(name: str) -> Any:
    if name not in _DB_ATTRS:
        raise AttributeError(name)
    module_name, attr_name = _DB_ATTRS[name]
    module = __import__(f"bike_analyzer.backend.db.{module_name}", fromlist=[attr_name])
    return getattr(module, attr_name)


__all__ = ["save_ride", "get_ride", "get_all_rides", "delete_ride", "init_db"]
