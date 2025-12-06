"""add hop metadata to message gateways

Revision ID: 6f8d2d9d3c5a
Revises: c5c3b86e6e72
Create Date: 2025-12-06 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f8d2d9d3c5a"
down_revision: Union[str, None] = "c5c3b86e6e72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "message_gateways",
        sa.Column("hop_limit_at_receipt", sa.Integer(), nullable=True),
    )
    op.add_column(
        "message_gateways",
        sa.Column("hops_travelled", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("message_gateways", "hops_travelled")
    op.drop_column("message_gateways", "hop_limit_at_receipt")

