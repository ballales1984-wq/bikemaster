"""API compatibility helpers.

Some tests / older codepaths expect database functions that were renamed or
removed during refactors. This module provides backward-compatible shims.
"""

from __future__ import annotations

from typing import Any


def get_athlete_by_query(db_database_module: Any, **query: Any) -> dict | None:
    """Compatibility helper for get_athlete_by_query.

    Supported query keys:
      - name: maps to get_athlete_by_name(name)
    """

    if not query:
        return None

    if "name" in query:
        name = query.get("name")
        if name is None:
            return None
        return db_database_module.get_athlete_by_name(str(name))

    return None
