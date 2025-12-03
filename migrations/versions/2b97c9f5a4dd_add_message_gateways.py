"""add message gateways table

Revision ID: 2b97c9f5a4dd
Revises: 1ff716849e6e
Create Date: 2025-11-30 06:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b97c9f5a4dd"
down_revision: Union[str, None] = "1ff716849e6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_gateways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "gateway_id", name="uq_message_gateways_message_gateway"),
    )
    op.create_index(op.f("ix_message_gateways_message_id"), "message_gateways", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_message_gateways_message_id"), table_name="message_gateways")
    op.drop_table("message_gateways")



