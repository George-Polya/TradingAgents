"""rename_members_to_member

Revision ID: h8i9j0k1l234
Revises: 2c50cb22c8eb
Create Date: 2025-07-16 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l234'
down_revision: Union[str, None] = '2c50cb22c8eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing foreign key constraints that reference members table
    op.drop_constraint('analysis_member_id_fkey', 'analysis', type_='foreignkey')
    op.drop_constraint('refresh_token_member_id_fkey', 'refresh_token', type_='foreignkey')
    
    # Drop RLS policies for members table
    op.execute("DROP POLICY IF EXISTS enable_read_access ON members")
    op.execute("DROP POLICY IF EXISTS enable_insert_access ON members")
    op.execute("DROP POLICY IF EXISTS enable_update_access ON members")
    op.execute("DROP POLICY IF EXISTS enable_delete_access ON members")
    
    # Rename table from members to member
    op.rename_table('members', 'member')
    
    # Create new foreign key constraints with updated references
    op.create_foreign_key('analysis_member_id_fkey', 'analysis', 'member', ['member_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('refresh_token_member_id_fkey', 'refresh_token', 'member', ['member_id'], ['id'], ondelete='CASCADE')
    
    # Create new RLS policies for member table
    op.execute("""
        CREATE POLICY "enable_read_access" ON member 
        FOR SELECT USING (true)
    """)
    op.execute("""
        CREATE POLICY "enable_insert_access" ON member 
        FOR INSERT WITH CHECK (true)
    """)
    op.execute("""
        CREATE POLICY "enable_update_access" ON member 
        FOR UPDATE USING (true)
    """)
    op.execute("""
        CREATE POLICY "enable_delete_access" ON member 
        FOR DELETE USING (true)
    """)


def downgrade() -> None:
    # Drop new RLS policies
    op.execute("DROP POLICY IF EXISTS enable_read_access ON member")
    op.execute("DROP POLICY IF EXISTS enable_insert_access ON member")
    op.execute("DROP POLICY IF EXISTS enable_update_access ON member")
    op.execute("DROP POLICY IF EXISTS enable_delete_access ON member")
    
    # Drop new foreign key constraints
    op.drop_constraint('analysis_member_id_fkey', 'analysis', type_='foreignkey')
    op.drop_constraint('refresh_token_member_id_fkey', 'refresh_token', type_='foreignkey')
    
    # Rename table back to members
    op.rename_table('member', 'members')
    
    # Restore original foreign key constraints
    op.create_foreign_key('analysis_member_id_fkey', 'analysis', 'members', ['member_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('refresh_token_member_id_fkey', 'refresh_token', 'members', ['member_id'], ['id'], ondelete='CASCADE')
    
    # Restore original RLS policies
    op.execute("""
        CREATE POLICY "enable_read_access" ON members 
        FOR SELECT USING (true)
    """)
    op.execute("""
        CREATE POLICY "enable_insert_access" ON members 
        FOR INSERT WITH CHECK (true)
    """)
    op.execute("""
        CREATE POLICY "enable_update_access" ON members 
        FOR UPDATE USING (true)
    """)
    op.execute("""
        CREATE POLICY "enable_delete_access" ON members 
        FOR DELETE USING (true)
    """)