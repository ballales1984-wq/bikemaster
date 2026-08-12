"""PostgreSQL stubs for non-migrated domains.

These functions raise ``RuntimeError`` when invoked on the managed PostgreSQL
backend (Render). They exist to satisfy the ``@pg_dispatch`` decorator's
lazy import mechanism: when ``DATABASE_URL`` is configured the decorator
attempts to import the matching symbol from this module; without it the
import fails with ``ModuleNotFoundError`` and crashes startup.

Currently no database functions point to this module; all migrated domains
live in their own ``postgres_*.py`` modules.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _not_migrated(fn_name: str) -> None:
    raise RuntimeError(
        f"[postgres_stubs] '{fn_name}' is not yet migrated to PostgreSQL. "
        "This domain still uses the local SQLite store."
    )
