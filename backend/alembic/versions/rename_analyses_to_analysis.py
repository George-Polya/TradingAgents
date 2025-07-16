"""rename_analyses_to_analysis

Revision ID: g7h8i9j0k123
Revises: f6g7h8i9j012
Create Date: 2025-07-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7h8i9j0k123'
down_revision: Union[str, None] = 'f6g7h8i9j012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint('analyses_member_id_fkey', 'analyses', type_='foreignkey')
    
    # Rename table from analyses to analysis
    op.rename_table('analyses', 'analysis')
    
    # Create new foreign key constraint with updated name
    op.create_foreign_key('analysis_member_id_fkey', 'analysis', 'members', ['member_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Drop the new foreign key constraint
    op.drop_constraint('analysis_member_id_fkey', 'analysis', type_='foreignkey')
    
    # Rename table back to analyses
    op.rename_table('analysis', 'analyses')
    
    # Restore original foreign key constraint
    op.create_foreign_key('analyses_member_id_fkey', 'analyses', 'members', ['member_id'], ['id'], ondelete='CASCADE')