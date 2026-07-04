"""merge_add_users

Revision ID: bbe692252c5e
Revises: add_pgvector_knowledge_chunks, cf_tenant_id_consolidated, 9f8e7d6c5b4a
Create Date: 2026-06-27 11:54:50.987825

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "bbe692252c5e"
down_revision: str | Sequence[str] | None = (
    "add_pgvector_knowledge_chunks",
    "cf_tenant_id_consolidated",
    "9f8e7d6c5b4a",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
