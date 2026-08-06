"""Shared helpers for Alembic migration scripts.

Provides idempotent wrappers around common ``op`` calls so that migrations
work correctly on both fresh databases (where tables were just created by
an earlier migration) and existing databases (where the table may already
have the column/index/constraint).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op


def table_exists(table_name: str, schema: str | None = None) -> bool:
    """Return True if *table_name* exists in the current bind."""
    inspector = inspect(op.get_bind())
    return inspector.has_table(table_name, schema)


def column_exists(table_name: str, column_name: str) -> bool:
    """Return True if *column_name* exists in *table_name*."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def index_exists(table_name: str, index_name: str) -> bool:
    """Return True if *index_name* exists on *table_name*."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Return True if a unique constraint *constraint_name* exists on *table_name*."""
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(c["name"] == constraint_name for c in inspector.get_unique_constraints(table_name))


def create_table_if_not_exists(table_obj: sa.Table) -> None:
    """Create *table_obj* only when it does not already exist (idempotent)."""
    if not table_exists(table_obj.name):
        op.create_table(table_obj)
