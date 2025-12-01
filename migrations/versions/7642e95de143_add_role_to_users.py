"""add_role_to_users

Revision ID: 7642e95de143
Revises: 17be1cb500c7
Create Date: 2025-12-01 08:03:59.010610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7642e95de143'
down_revision: Union[str, None] = '17be1cb500c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to users table
    op.add_column('users', sa.Column('role', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)


def downgrade() -> None:
    # Remove role column from users table
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_column('users', 'role')
