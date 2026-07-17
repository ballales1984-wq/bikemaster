"""add_is_client_to_users

Revision ID: add_is_client_col
Revises: bbe692252c5e
Create Date: 2026-07-17 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_is_client_col"
down_revision: str | Sequence[str] | None = "add_chat_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the is_client column to the users table if missing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}
    if "is_client" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "is_client",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    """Remove the is_client column from the users table if present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("users")}
    if "is_client" in existing:
        op.drop_column("users", "is_client")
