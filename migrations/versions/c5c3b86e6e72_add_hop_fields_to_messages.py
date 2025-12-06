"""add hop metadata to messages

Revision ID: c5c3b86e6e72
Revises: 7642e95de143
Create Date: 2025-12-06 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5c3b86e6e72"
down_revision: Union[str, None] = "7642e95de143"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("hop_start", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("hop_limit", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "hop_limit")
    op.drop_column("messages", "hop_start")

