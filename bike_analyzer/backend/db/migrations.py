"""Run Alembic database migrations on application startup.

This keeps the production schema in sync without a separate deploy step: when the
app boots with a configured ``DATABASE_URL`` it runs ``alembic upgrade head`` (a
no-op if migrations are already applied). Disabled by default so it can be opted
out via ``RUN_MIGRATIONS_ON_STARTUP=0`` (e.g. when a separate migration job runs).
"""

from __future__ import annotations

import os
from logging import getLogger

logger = getLogger(__name__)


def run_migrations_on_startup() -> bool:
    """Apply pending Alembic migrations. Returns True if migrations ran."""
    if os.getenv("RUN_MIGRATIONS_ON_STARTUP", "1").lower() in {"0", "false", "no"}:
        logger.info("Migrations on startup disabled (RUN_MIGRATIONS_ON_STARTUP)")
        return False

    from bike_analyzer.backend.settings import get_settings

    settings = get_settings()
    if not settings.database_url:
        logger.info("No DATABASE_URL configured, skipping migrations")
        return False

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
        migration_url = os.environ.get("DATABASE_URL_UNPOOLED") or settings.database_url
        cfg.set_main_option("sqlalchemy.url", migration_url)
        command.upgrade(cfg, "head")
        logger.info("Database migrations applied (alembic upgrade head)")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to apply database migrations")
        return False
