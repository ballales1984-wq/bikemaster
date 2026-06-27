"""merge_add_users

Revision ID: bbe692252c5e
Revises: add_pgvector_knowledge_chunks, add_tenant_id, 9f8e7d6c5b4a, 1a2b3c4d5e6f
Create Date: 2026-06-27 11:54:50.987825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbe692252c5e'
down_revision: Union[str, Sequence[str], None] = ('add_pgvector_knowledge_chunks', 'add_tenant_id', '9f8e7d6c5b4a', '1a2b3c4d5e6f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
