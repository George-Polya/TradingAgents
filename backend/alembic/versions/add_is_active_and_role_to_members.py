"""add_is_active_and_role_to_members

Revision ID: c3d4e5f6g789
Revises: b9b6cdf75981
Create Date: 2025-07-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g789'
down_revision: Union[str, None] = 'b9b6cdf75981'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create role enum type
    role_enum = postgresql.ENUM('ADMIN', 'USER', name='role')
    role_enum.create(op.get_bind())
    
    # Add is_active column
    op.add_column('members', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Add role column
    op.add_column('members', sa.Column('role', sa.Enum('ADMIN', 'USER', name='role'), nullable=False, server_default='USER'))


def downgrade() -> None:
    # Remove columns
    op.drop_column('members', 'role')
    op.drop_column('members', 'is_active')
    
    # Drop enum type
    role_enum = postgresql.ENUM('ADMIN', 'USER', name='role')
    role_enum.drop(op.get_bind())