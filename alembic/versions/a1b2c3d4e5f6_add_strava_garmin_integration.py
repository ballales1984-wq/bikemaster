"""add_strava_garmin_integration

Revision ID: a1b2c3d4e5f6
Revises: 08ee39bfe529
Create Date: 2026-06-14 17:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "08ee39bfe529"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    op.create_table(
        "strava_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.String(length=1024), nullable=False),
        sa.Column("refresh_token", sa.String(length=1024), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=200), nullable=True),
        sa.Column("athlete_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_strava_tokens_athlete", "strava_tokens", ["athlete_id"], unique=True)
    op.create_table(
        "garmin_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("access_token", sa.String(length=1024), nullable=False),
        sa.Column("refresh_token", sa.String(length=1024), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=200), nullable=True),
        sa.Column("athlete_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_garmin_tokens_athlete", "garmin_tokens", ["athlete_id"], unique=True)
    if not _has_column("rides", "external_source"):
        op.add_column("rides", sa.Column("external_source", sa.String(length=50), nullable=True))
    if not _has_column("rides", "external_id"):
        op.add_column("rides", sa.Column("external_id", sa.String(length=100), nullable=True))
    if not _has_column("rides", "title"):
        op.add_column("rides", sa.Column("title", sa.String(length=200), nullable=True))
    if not _has_column("rides", "external_source") or not _has_column("rides", "external_id"):
        op.create_index("ix_rides_external_source", "rides", ["external_source", "external_id"], unique=False)


def downgrade() -> None:
    try:
        op.drop_index("ix_rides_external_source", table_name="rides")
    except Exception:
        pass
    try:
        op.drop_column("rides", "title")
    except Exception:
        pass
    try:
        op.drop_column("rides", "external_id")
    except Exception:
        pass
    try:
        op.drop_column("rides", "external_source")
    except Exception:
        pass
    try:
        op.drop_index("ix_garmin_tokens_athlete", table_name="garmin_tokens")
    except Exception:
        pass
    try:
        op.drop_table("garmin_tokens")
    except Exception:
        pass
    try:
        op.drop_index("ix_strava_tokens_athlete", table_name="strava_tokens")
    except Exception:
        pass
    try:
        op.drop_table("strava_tokens")
    except Exception:
        pass
