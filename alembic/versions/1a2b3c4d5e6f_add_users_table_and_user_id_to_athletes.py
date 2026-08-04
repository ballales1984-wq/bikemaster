"""add_users_table_and_user_id_to_athletes

Revision ID: 1a2b3c4d5e6f
Revises: cf_tenant_id_consolidated
Create Date: 2026-06-27 11:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect
from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "cf_tenant_id_consolidated"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    def _has_col(table_name: str, col_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return any(c["name"] == col_name for c in inspector.get_columns(table_name))

    def _has_idx(table_name: str, idx_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return any(idx["name"] == idx_name for idx in inspector.get_indexes(table_name))

    if not inspector.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("password_hash", sa.String(length=255), nullable=True),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("username", name="uq_users_username"),
            sa.UniqueConstraint("email", name="uq_users_email"),
            sa.Index("ix_users_username", "username", unique=False),
            sa.Index("ix_users_email", "email", unique=False),
            sa.PrimaryKeyConstraint("id"),
        )

    # Add user_id to athletes and create index — direct ops on PostgreSQL
    if not _has_col("athletes", "user_id"):
        op.add_column("athletes", sa.Column("user_id", sa.Integer(), nullable=True))
    if not _has_idx("athletes", "ix_athletes_user"):
        op.create_index("ix_athletes_user", "athletes", ["user_id"], unique=False)

    # Change password_hash from Text to String(255) — needs batch on SQLite
    if is_pg:
        if _has_col("athletes", "password_hash"):
            op.alter_column(
                "athletes", "password_hash",
                existing_type=sa.Text(),
                type_=sa.String(length=255),
                existing_nullable=True,
            )
    else:
        with op.batch_alter_table("athletes", schema=None) as batch_op:
            batch_op.alter_column(
                "password_hash",
                existing_type=sa.Text(),
                type_=sa.String(length=255),
                existing_nullable=True,
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("athletes"):
        return

    def _has_idx(table_name: str, idx_name: str) -> bool:
        return any(idx["name"] == idx_name for idx in inspector.get_indexes(table_name))

    def _has_col(table_name: str, col_name: str) -> bool:
        return any(c["name"] == col_name for c in inspector.get_columns(table_name))

    is_pg = bind.dialect.name == "postgresql"

    if _has_idx("athletes", "ix_athletes_user"):
        if is_pg:
            op.drop_index("ix_athletes_user", table_name="athletes")
        else:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.drop_index("ix_athletes_user")

    if _has_col("athletes", "user_id"):
        if is_pg:
            op.drop_column("athletes", "user_id")
        else:
            with op.batch_alter_table("athletes", schema=None) as batch_op:
                batch_op.drop_column("user_id")

    if inspector.has_table("users"):
        op.drop_table("users")
