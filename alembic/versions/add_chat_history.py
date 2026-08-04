"""add chat_history table for persistent AI Coach conversations.

Mirrors the SQLite ``chat_history`` table used by the sync layer so the async
PostgreSQL path persists per-user conversation memory as well. This migration also
merges the two pre-existing heads (``bbe692252c5e`` and ``1a2b3c4d5e6f``) into a
single head so ``alembic upgrade head`` works.

Revision ID: add_chat_history
Revises: bbe692252c5e, 1a2b3c4d5e6f
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "add_chat_history"
down_revision: str | Sequence[str] | None = ("bbe692252c5e", "1a2b3c4d5e6f")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("chat_history"):
        op.create_table(
            "chat_history",
            sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
            sa.Column("athlete_id", sa.INTEGER(), nullable=True),
            sa.Column("tenant_id", sa.INTEGER(), nullable=False, server_default="0"),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if inspector.has_table("chat_history"):
        _idx = {idx["name"] for idx in inspector.get_indexes("chat_history")}
        if "ix_chat_history_athlete_id" not in _idx:
            op.create_index("ix_chat_history_athlete_id", "chat_history", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_history_athlete_id", table_name="chat_history")
    op.drop_table("chat_history")
