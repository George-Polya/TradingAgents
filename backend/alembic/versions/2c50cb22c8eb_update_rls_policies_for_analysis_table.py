"""update_rls_policies_for_analysis_table

Revision ID: 2c50cb22c8eb
Revises: g7h8i9j0k123
Create Date: 2025-07-16 19:43:42.646065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c50cb22c8eb'
down_revision: Union[str, None] = 'g7h8i9j0k123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old RLS policies that reference 'analyses' table
    op.execute("DROP POLICY IF EXISTS \"Users can delete own analyses\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can update own analyses\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can create own analyses\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can view own analyses\" ON analysis")
    
    # Create new RLS policies for 'analysis' table
    op.execute("""
        CREATE POLICY "Users can view own analysis" ON analysis
        FOR SELECT USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can create own analysis" ON analysis
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can update own analysis" ON analysis
        FOR UPDATE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can delete own analysis" ON analysis
        FOR DELETE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    # Update indexes to use singular naming convention
    op.execute("DROP INDEX IF EXISTS idx_analyses_member_id")
    op.execute("DROP INDEX IF EXISTS idx_analyses_ticker")
    op.create_index('idx_analysis_member_id', 'analysis', ['member_id'])
    op.create_index('idx_analysis_ticker', 'analysis', ['ticker'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('idx_analysis_ticker', 'analysis')
    op.drop_index('idx_analysis_member_id', 'analysis')
    
    # Recreate old indexes
    op.create_index('idx_analyses_member_id', 'analysis', ['member_id'])
    op.create_index('idx_analyses_ticker', 'analysis', ['ticker'])
    
    # Drop new RLS policies
    op.execute("DROP POLICY IF EXISTS \"Users can delete own analysis\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can update own analysis\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can create own analysis\" ON analysis")
    op.execute("DROP POLICY IF EXISTS \"Users can view own analysis\" ON analysis")
    
    # Recreate old RLS policies
    op.execute("""
        CREATE POLICY "Users can view own analyses" ON analysis
        FOR SELECT USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can create own analyses" ON analysis
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can update own analyses" ON analysis
        FOR UPDATE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can delete own analyses" ON analysis
        FOR DELETE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
