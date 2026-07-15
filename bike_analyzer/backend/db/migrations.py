"""Run Alembic database migrations on application startup.

Keeps the database schema in sync without a separate deploy step. SQLite is the
local-first PRIMARY store (managed by ``db/database.py::init_db``), so Alembic
migrations are applied to whichever database is the *active* target:

* Optional cloud sync **PostgreSQL** when ``DATABASE_URL`` is configured.
* The local **SQLite** primary store only when ``RUN_LOCAL_MIGRATIONS=1`` is set
  (off by default, because the hand-managed SQLite schema is owned by ``init_db``).

Migrations are disabled entirely when ``RUN_MIGRATIONS_ON_STARTUP=0`` (e.g. when
a separate migration job runs).
"""

from __future__ import annotations

import os
from logging import getLogger

logger = getLogger(__name__)


def _run_alembic(migration_url: str) -> bool:
    """Apply pending Alembic migrations against ``migration_url``."""
    try:
        from alembic.config import Config

        from alembic import command
    except ImportError:
        logger.warning("alembic not installed, skipping migrations")
        return False

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ini_path = os.path.join(repo_root, "alembic.ini")
    if not os.path.exists(ini_path):
        logger.warning("alembic.ini not found at %s, skipping migrations", ini_path)
        return False

    try:
        cfg = Config(ini_path)
        cfg.set_main_option("sqlalchemy.url", migration_url)
        command.upgrade(cfg, "head")
        logger.info("Database migrations applied (alembic upgrade head) -> %s", migration_url)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to apply database migrations")
        return False


def run_migrations_on_startup() -> bool:
    """Apply pending Alembic migrations. Returns True if migrations ran."""
    if os.getenv("RUN_MIGRATIONS_ON_STARTUP", "1").lower() in {"0", "false", "no"}:
        logger.info("Migrations on startup disabled (RUN_MIGRATIONS_ON_STARTUP)")
        return False

    from bike_analyzer.backend.settings import get_settings

    settings = get_settings()
    database_url = getattr(settings, "database_url", "") or ""
    database_url_unpooled = getattr(settings, "database_url_unpooled", "") or ""
    db_path = getattr(settings, "db_path", "rides.db") or "rides.db"

    # Optional cloud sync PostgreSQL: migrate it when configured.
    cloud_url = (database_url or database_url_unpooled or "").strip()
    if cloud_url:
        migration_url = os.environ.get("DATABASE_URL_UNPOOLED") or database_url
        return _run_alembic(migration_url)

    # Local SQLite primary is owned by init_db() by default. Opt-in only.
    if os.getenv("RUN_LOCAL_MIGRATIONS", "0").lower() not in {"1", "true", "yes"}:
        logger.info(
            "No cloud DATABASE_URL; local SQLite primary (db_path=%s) is managed by "
            "init_db(). Set RUN_LOCAL_MIGRATIONS=1 to also apply Alembic migrations locally.",
            db_path,
        )
        return False
    return _run_alembic(f"sqlite:///{db_path}")
