"""add_users_table_and_user_id_fix

Revision ID: add_users_table_and_user_id_fix
Revises: multi_athlete_per_user_and_oauth_credentials
Create Date: 2026-08-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "add_users_table_and_user_id_fix"
down_revision: Union[str, Sequence[str], None] = "multi_athlete_per_user_and_oauth_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if not _has_table("users"):
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

    inspector = inspect(bind)

    def _has_idx(table_name: str, idx_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return any(idx["name"] == idx_name for idx in inspector.get_indexes(table_name))

    if not _has_column("athletes", "user_id"):
        op.add_column("athletes", sa.Column("user_id", sa.Integer(), nullable=True))
    if not _has_idx("athletes", "ix_athletes_user"):
        op.create_index("ix_athletes_user", "athletes", ["user_id"], unique=False)

    if _has_unique_constraint("athletes", "uq_athletes_user_id"):
        if is_pg:
            op.drop_constraint("uq_athletes_user_id", "athletes", type_="unique")
        else:
            with op.batch_alter_table("athletes") as batch_op:
                batch_op.drop_constraint("uq_athletes_user_id", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if _has_unique_constraint("athletes", "uq_athletes_user_id"):
        pass
    else:
        try:
            if is_pg:
                op.create_unique_constraint("uq_athletes_user_id", "athletes", ["user_id"])
            else:
                with op.batch_alter_table("athletes") as batch_op:
                    batch_op.create_unique_constraint("uq_athletes_user_id", ["user_id"])
        except Exception:
            pass

    inspector = inspect(bind)

    def _has_idx(table_name: str, idx_name: str) -> bool:
        if not inspector.has_table(table_name):
            return False
        return any(idx["name"] == idx_name for idx in inspector.get_indexes(table_name))

    if _has_column("athletes", "user_id"):
        if is_pg:
            if _has_idx("athletes", "ix_athletes_user"):
                op.drop_index("ix_athletes_user", table_name="athletes")
            op.drop_column("athletes", "user_id")
        else:
            with op.batch_alter_table("athletes") as batch_op:
                batch_op.drop_index("ix_athletes_user")
                batch_op.drop_column("user_id")

    if _has_table("users"):
        op.drop_table("users")
