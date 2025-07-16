"""rename_refresh_tokens_to_refresh_token

Revision ID: e5f6g7h8i901
Revises: d4e5f6g7h890
Create Date: 2025-07-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i901'
down_revision: Union[str, None] = 'd4e5f6g7h890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint('refresh_tokens_member_id_fkey', 'refresh_tokens', type_='foreignkey')
    
    # Rename table from refresh_tokens to refresh_token
    op.rename_table('refresh_tokens', 'refresh_token')
    
    # Create new foreign key constraint with updated name
    op.create_foreign_key('refresh_token_member_id_fkey', 'refresh_token', 'members', ['member_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Drop the new foreign key constraint
    op.drop_constraint('refresh_token_member_id_fkey', 'refresh_token', type_='foreignkey')
    
    # Rename table back to refresh_tokens
    op.rename_table('refresh_token', 'refresh_tokens')
    
    # Restore original foreign key constraint
    op.create_foreign_key('refresh_tokens_member_id_fkey', 'refresh_tokens', 'members', ['member_id'], ['id'], ondelete='CASCADE')