"""Centralized SQLite / PostgreSQL dispatch layer.

This module is THE single source of truth for the "are we running on the local
SQLite store or the managed PostgreSQL backend?" question.

Before this module existed the decision was duplicated by hand inside 30+
functions in :mod:`database.py`, each carrying its own copy of::

    from .postgres_rides import has_postgres, save_ride as _pg_save_ride
    if has_postgres():
        return _pg_save_ride(...)

That made it impossible to tell, at a glance, whether a given domain function
was migrated to PostgreSQL or not.  The ``pg_dispatch`` decorator below
replaces every such block with a single line, and :data:`MIGRATED_TABLES`
documents the full migration boundary in one place.

Usage (in ``database.py``)::

    from .dispatch import pg_dispatch

    @pg_dispatch("bike_analyzer.backend.db.postgres_rides")
    def save_ride(ride: dict) -> int:
        \"\"\"...sqlite implementation, no inline dispatch...\"\"\"
        ...

The PostgreSQL implementation is imported **lazily** (only when
``is_postgres()`` is true *and* the function is actually called), preserving
the existing behaviour where psycopg2 / postgres modules are never imported in
a SQLite-only (e.g. Tauri) environment.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from functools import wraps
from typing import Any

from ..settings import get_settings

_s = get_settings()


def _pg_url() -> str:
    """Mirror the exact logic in ``postgres_athlete._url`` so a single env
    variable (``DATABASE_URL``) is the only trigger — no drift."""
    return (
        os.environ.get("DATABASE_URL") or _s.database_url or ""
    ).strip()


def is_postgres() -> bool:
    """Single source of truth: True when the managed PostgreSQL backend is active."""
    return bool(_pg_url())


# --------------------------------------------------------------------------- #
# Migration boundary registry
# --------------------------------------------------------------------------- #
# One glance at this dict tells you which domains have been migrated off the
# ephemeral SQLite store onto the managed PostgreSQL database (Render).
# Anything NOT listed here is SQLite-only: on a cloud container without a
# persistent volume, those tables lose their data on every suspend/resume.
#
# Format:  domain_key -> (python module path, [function names mirrored in database.py])
POSTGRES_BACKENDS: dict[str, tuple[str, list[str]]] = {
    # Athlete profile + metric log + history + snapshots
    "athlete": (
        "bike_analyzer.backend.db.postgres_athlete",
        [
            "get_athlete",
            "save_athlete",
            "update_athlete",
            "get_athlete_by_email",
            "save_athlete_snapshot",
            "get_athlete_history",
            "get_athletes_by_user",
            "get_athlete_count_by_user",
            "delete_athlete",
            "log_athlete_metric",
            "get_athlete_metric_log",
            "get_all_athletes",
        ],
    ),
    # Rides / metrics / training stress (TSS, ATL, CTL, TSB)
    "rides": (
        "bike_analyzer.backend.db.postgres_rides",
        [
            "save_ride",
            "get_ride",
            "get_rides_by_athlete",
            "get_all_rides",
            "delete_ride",
            "update_ride",
            "save_metric",
            "get_metrics_by_athlete",
            "upsert_training_stress_day",
            "get_training_stress_days",
            "get_latest_training_stress",
        ],
    ),
    # Itineraries + stages (multi-day route planning)
    "itineraries": (
        "bike_analyzer.backend.db.postgres_itineraries",
        [
            "save_itinerary",
            "get_itinerary",
            "list_itineraries",
            "update_itinerary",
            "delete_itinerary",
            "save_stage",
            "list_stages",
            "get_stage",
            "update_stage",
            "delete_stage",
            "reorder_stages",
        ],
    ),
    # Users (authentication + profile)
    "users": (
        "bike_analyzer.backend.db.postgres_users",
        [
            "save_user",
            "get_user_by_username",
            "get_user_by_id",
            "get_all_users",
            "update_user",
            "delete_user",
        ],
    ),
    # Calendar events
    "calendar": (
        "bike_analyzer.backend.db.postgres_calendar",
        [
            "save_calendar_event",
            "get_calendar_event",
            "get_events_by_athlete",
            "get_events_by_date_range",
            "get_events_by_month",
            "update_calendar_event",
            "delete_calendar_event",
        ],
    ),
    # OAuth provider tokens (Strava / Garmin / Wahoo)
    "oauth_tokens": (
        "bike_analyzer.backend.db.postgres_oauth_tokens",
        [
            "save_strava_token",
            "get_strava_token",
            "revoke_strava_token",
            "update_strava_last_sync",
            "save_garmin_token",
            "get_garmin_token",
            "revoke_garmin_token",
            "save_wahoo_token",
            "get_wahoo_token",
            "revoke_wahoo_token",
        ],
    ),
    # Google OAuth tokens
    "google_oauth": (
        "bike_analyzer.backend.db.postgres_google_oauth",
        [
            "save_google_token",
            "get_google_token",
            "delete_google_token",
        ],
    ),
    # Health Connect
    "health_connect": (
        "bike_analyzer.backend.db.postgres_health_connect",
        [
            "connect_health_connect",
            "disconnect_health_connect",
            "get_health_connect_token",
            "update_health_connect_sync",
        ],
    ),
    # Security (revoked JWT tokens)
    "security": (
        "bike_analyzer.backend.db.postgres_security",
        [
            "revoke_token",
            "is_token_revoked",
            "sweep_revoked_tokens",
        ],
    ),
    # Sync metadata
    "sync": (
        "bike_analyzer.backend.db.postgres_sync",
        [
            "save_sync_entity_state",
            "get_sync_entity_state",
            "save_sync_setting",
            "get_sync_setting",
            "save_sync_conflict",
            "get_pending_sync_entities",
            "get_sync_conflicts",
            "resolve_sync_conflict",
        ],
    ),
    # Maps (SerpApi usage)
    "maps": (
        "bike_analyzer.backend.db.postgres_maps",
        [
            "get_maps_usage",
            "record_maps_call",
        ],
    ),
}
# NOTE: ``training_goals`` are persisted via ``postgres_db`` / ``async_db``
# (SQLAlchemy) directly from routes — they have no SQLite twin in database.py,
# so they are out of scope for the ``@pg_dispatch`` decorator.

# Flat reverse lookup: sqlite function name -> postgres module dotted path
MIGRATED_FUNCTIONS: dict[str, str] = {
    fn: pg_module_path
    for pg_module_path, fns in POSTGRES_BACKENDS.values()
    for fn in fns
}


def _get_pg_fn(pg_module_name: str, fn_name: str) -> Callable[..., Any]:
    """Lazily import and return the PostgreSQL mirror of ``database.py``'s
    ``fn_name``.  Import is deferred so psycopg2 is never loaded in a
    SQLite-only environment."""
    mod = importlib.import_module(pg_module_name)
    return getattr(mod, fn_name)


def pg_dispatch(pg_module_name: str) -> Callable[[Callable], Callable]:
    """Decorator that replaces the inline ``if has_postgres(): return _pg(...)``
    blocks scattered across ``database.py``.

    The decorated function keeps its SQLite body as the fallback; when the
    PostgreSQL backend is active the matching function (same name) is imported
    from ``pg_module_name`` and invoked with the **exact same arguments** the
    caller originally passed — no argument translation needed.

    Metadata ``_pg_module`` / ``_is_postgres`` is attached so tests and tooling
    can introspect the dispatch without parsing source code.
    """
    def decorator(sqlite_fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(sqlite_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if is_postgres():
                return _get_pg_fn(pg_module_name, sqlite_fn.__name__)(*args, **kwargs)
            return sqlite_fn(*args, **kwargs)

        wrapper._pg_module = pg_module_name          # noqa: SLF001
        wrapper._sqlite_impl = sqlite_fn             # noqa: SLF001
        wrapper._dispatch_source = "pg_dispatch"      # noqa: SLF001
        wrapper._is_postgres = staticmethod(is_postgres)  # noqa: SLF001
        return wrapper

    return decorator
