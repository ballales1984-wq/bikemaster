"""Verify the layered architecture invariant enforced by AGENTS.md §2:

    Router -> Service -> Repository -> Database

No Service-layer module may import ``db.database`` (Database) or the
``api.user_keys`` HTTP module (API layer) — the two anti-dependencies.

Checks are AST/source-based so they also catch *lazy* in-function imports
(where the old violations lived, e.g. ``from ..db.database import ...`` inside
a function body). They never import the modules under test, so they are immune
to the pre-existing ``db.database`` load-time cycle.
"""

from __future__ import annotations

import ast
import importlib.util


def _imported_modules_in(source: str, package: str) -> list[str]:
    """Module paths referenced by Import / ImportFrom nodes, relatives resolved
    against ``package``."""
    tree = ast.parse(source)
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = package
            for _ in range(node.level - 1):
                base = base.rsplit(".", 1)[0]
            if node.module:
                out.append(base + "." + node.module if (base and node.module) else (node.module or ""))
            else:
                out.append(base)
    return out


def _assert_no_edge(dotted: str, package: str, forbidden: list[str]) -> None:
    """Parse a module's *source* (never importing it) so the acyclicity check is
    not poisoned by pre-existing import-time cycles elsewhere in the codebase."""
    spec = importlib.util.find_spec(dotted)
    assert spec is not None and spec.origin, f"cannot locate {dotted}"
    with open(spec.origin, encoding="utf-8") as fh:
        source = fh.read()
    bad = [m for m in _imported_modules_in(source, package) if any(f in m for f in forbidden)]
    assert not bad, f"forbidden import edge(s): {bad} (patterns: {forbidden}) in {package}"


_FORBIDDEN = ["db.database", "api.user_keys"]
WEATHER_PKG = "bike_analyzer.backend.weather"
AI_COACH_PKG = "bike_analyzer.backend.analytics"
PROVIDER_PKG = "bike_analyzer.backend"


def test_weather_service_has_no_database_or_api_dependency():
    _assert_no_edge("bike_analyzer.backend.weather.weather_service", WEATHER_PKG, _FORBIDDEN)


def test_ai_coach_has_no_database_or_api_dependency():
    _assert_no_edge("bike_analyzer.backend.analytics.ai_coach", AI_COACH_PKG, _FORBIDDEN)


def test_user_keys_provider_is_infra_not_api():
    """user_keys_provider is a transport-agnostic infra abstraction: it must
    not import the api.user_keys HTTP module (the layer it decouples from)."""
    _assert_no_edge("bike_analyzer.backend.user_keys_provider", PROVIDER_PKG, _FORBIDDEN)


# ---------------------------------------------------------------------------
# Repository structure + Service -> Repository wiring
# ---------------------------------------------------------------------------


def test_weather_repository_exposes_cache_methods():
    from bike_analyzer.backend.weather.repositories.weather_repository import WeatherRepository

    assert callable(getattr(WeatherRepository, "get_weather_cache", None))
    assert callable(getattr(WeatherRepository, "save_weather_cache", None))


def test_weather_service_uses_repository_for_cache(monkeypatch):
    """get_weather_for_coordinates reads/writes cache via WeatherRepository,
    never via a direct db.database import in the service."""
    from bike_analyzer.backend.weather import weather_service
    from bike_analyzer.backend.weather.repositories.weather_repository import WeatherRepository

    monkeypatch.setattr(
        WeatherRepository,
        "get_weather_cache",
        staticmethod(lambda lat, lon, date: {"cached": True, "temperature": 1, "humidity": 2}),
    )
    monkeypatch.setattr(
        WeatherRepository,
        "save_weather_cache",
        staticmethod(lambda lat, lon, date, weather: 1),
    )
    monkeypatch.setattr(weather_service, "_get_weather_api_key", lambda provider=None: "fake_key")

    result = weather_service.get_weather_for_coordinates(45.0, 9.0)
    assert result == {"cached": True, "temperature": 1, "humidity": 2}
