"""multi_athlete_per_user_and_oauth_credentials

Revision ID: multi_athlete_per_user_and_oauth_credentials
Revises: change_pois_type_to_string
Create Date: 2026-08-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "multi_athlete_per_user_and_oauth_credentials"
down_revision: str | Sequence[str] | None = "change_pois_type_to_string"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uq_exists(table_name: str, uq_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(uq["name"] == uq_name for uq in inspector.get_unique_constraints(table_name))


def _idx_exists(table_name: str, idx_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(idx["name"] == idx_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    # Drop unique constraint on athletes.user_id (PostgreSQL: direct, SQLite: batch)
    if _uq_exists("athletes", "uq_athletes_user_id"):
        if is_pg:
            op.drop_constraint("uq_athletes_user_id", "athletes", type_="unique")
        else:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.drop_constraint("uq_athletes_user_id", type_="unique")

    # Create user_oauth_credentials table (already exists from 13a1d54d325f)
    if not inspector.has_table("user_oauth_credentials"):
        op.create_table(
            "user_oauth_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("client_id", sa.String(), nullable=True),
            sa.Column("client_secret", sa.String(), nullable=True),
            sa.Column("redirect_uri", sa.String(), nullable=True),
            sa.Column("scope", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "provider", name="uq_user_oauth_credentials_user_provider"),
        )
    if not _idx_exists("user_oauth_credentials", "ix_user_oauth_credentials_user"):
        op.create_index("ix_user_oauth_credentials_user", "user_oauth_credentials", ["user_id"])


def downgrade() -> None:
    if _idx_exists("user_oauth_credentials", "ix_user_oauth_credentials_user"):
        op.drop_index("ix_user_oauth_credentials_user", table_name="user_oauth_credentials")
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("user_oauth_credentials"):
        op.drop_table("user_oauth_credentials")

    if not _uq_exists("athletes", "uq_athletes_user_id"):
        if bind.dialect.name == "postgresql":
            op.create_unique_constraint("uq_athletes_user_id", "athletes", ["user_id"])
        else:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.create_unique_constraint("uq_athletes_user_id", ["user_id"])
