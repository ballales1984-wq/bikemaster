"""add_users_table_and_user_id_to_athletes

Revision ID: 1a2b3c4d5e6f
Revises: cf_tenant_id_consolidated
Create Date: 2026-06-27 11:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "cf_tenant_id_consolidated"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
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
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_athletes_user", ["user_id"], unique=False)
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("athletes", schema=None) as batch_op:
        batch_op.drop_index("ix_athletes_user")
        batch_op.drop_column("user_id")
    op.drop_table("users")
