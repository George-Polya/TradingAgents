"""add_revoked_columns_to_refresh_tokens

Revision ID: d4e5f6g7h890
Revises: c3d4e5f6g789
Create Date: 2025-07-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h890'
down_revision: Union[str, None] = 'c3d4e5f6g789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add revoked column with default value false
    op.add_column('refresh_tokens', 
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add revoked_at column (nullable)
    op.add_column('refresh_tokens', 
        sa.Column('revoked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('refresh_tokens', 'revoked_at')
    op.drop_column('refresh_tokens', 'revoked')