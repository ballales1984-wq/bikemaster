"""add_pgvector_knowledge_chunks

Revision ID: add_pgvector_knowledge_chunks
Revises: 08ee39bfe529
Create Date: 2026-06-17

"""

import contextlib
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_pgvector_knowledge_chunks"
down_revision: str | Sequence[str] | None = "08ee39bfe529"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    dialect = connection.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("chunk_id", sa.String(length=200), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.TEXT(), nullable=True),
        sa.Column("word_count", sa.INTEGER(), nullable=False, server_default="0"),
        sa.Column("char_count", sa.INTEGER(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.INTEGER(), nullable=False, server_default="0"),
        sa.Column("section", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_topic", "knowledge_chunks", ["topic"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column("athlete_id", sa.INTEGER(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_athlete_id", "chat_messages", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_athlete_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_knowledge_chunks_topic", table_name="knowledge_chunks")
    with contextlib.suppress(Exception):
        op.drop_index(
            "ix_knowledge_chunks_embedding",
            table_name="knowledge_chunks",
        )
    op.drop_table("knowledge_chunks")
