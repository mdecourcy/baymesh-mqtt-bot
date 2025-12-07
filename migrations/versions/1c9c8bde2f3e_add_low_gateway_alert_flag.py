"""add low_gateway_alert_sent flag to messages

Revision ID: 1c9c8bde2f3e
Revises: 6f8d2d9d3c5a
Create Date: 2025-12-07 05:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c9c8bde2f3e"
down_revision: Union[str, None] = "6f8d2d9d3c5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "low_gateway_alert_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "low_gateway_alert_sent")

