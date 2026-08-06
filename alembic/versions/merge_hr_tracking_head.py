"""merge heads: add_hr_24h_tracking and add_users_table_and_user_id_fix

Revision ID: merge_hr_tracking_head
Revises: add_hr_24h_tracking, add_users_table_and_user_id_fix
Create Date: 2026-08-04

Merges the two divergent heads (``add_hr_24h_tracking`` and
``add_users_table_and_user_id_fix``) into a single head so that
``alembic upgrade head`` works without a "Multiple heads" error on a
fresh PostgreSQL deployment.
"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "merge_hr_tracking_head"
down_revision: str | Sequence[str] | None = (
    "add_hr_24h_tracking",
    "add_users_table_and_user_id_fix",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
