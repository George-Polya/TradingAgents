"""Enable Row Level Security (RLS) on all tables

Revision ID: 003_enable_rls
Revises: c5fb62c802f1
Create Date: 2025-07-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_enable_rls'
down_revision = 'c5fb62c802f1'
branch_labels = None
depends_on = None


def upgrade():
    """
    Enable Row Level Security on all tables and create policies.
    Note: This migration assumes Supabase authentication is being used.
    If using custom JWT auth, the policies need to be adjusted.
    """
    
    # Enable RLS on all tables
    op.execute('ALTER TABLE members ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;')
    
    # Members table policies
    # Users can only view their own profile
    op.execute("""
        CREATE POLICY "Users can view own profile" ON members
        FOR SELECT USING (id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only update their own profile
    op.execute("""
        CREATE POLICY "Users can update own profile" ON members
        FOR UPDATE USING (id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can insert their own profile during registration
    op.execute("""
        CREATE POLICY "Users can create own profile" ON members
        FOR INSERT WITH CHECK (id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Analyses table policies
    # Users can only view their own analyses
    op.execute("""
        CREATE POLICY "Users can view own analyses" ON analyses
        FOR SELECT USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only create analyses for themselves
    op.execute("""
        CREATE POLICY "Users can create own analyses" ON analyses
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only update their own analyses
    op.execute("""
        CREATE POLICY "Users can update own analyses" ON analyses
        FOR UPDATE USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only delete their own analyses
    op.execute("""
        CREATE POLICY "Users can delete own analyses" ON analyses
        FOR DELETE USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Refresh tokens table policies
    # Users can only view their own refresh tokens
    op.execute("""
        CREATE POLICY "Users can view own refresh tokens" ON refresh_tokens
        FOR SELECT USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only create refresh tokens for themselves
    op.execute("""
        CREATE POLICY "Users can create own refresh tokens" ON refresh_tokens
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can only delete their own refresh tokens (for logout)
    op.execute("""
        CREATE POLICY "Users can delete own refresh tokens" ON refresh_tokens
        FOR DELETE USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)
    
    # Users can update their own refresh tokens (for revocation)
    op.execute("""
        CREATE POLICY "Users can update own refresh tokens" ON refresh_tokens
        FOR UPDATE USING (member_id = current_setting('app.current_user_id')::VARCHAR);
    """)


def downgrade():
    """
    Disable Row Level Security and drop all policies
    """
    
    # Drop all policies first
    # Members table
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON members;')
    op.execute('DROP POLICY IF EXISTS "Users can update own profile" ON members;')
    op.execute('DROP POLICY IF EXISTS "Users can create own profile" ON members;')
    
    # Analyses table
    op.execute('DROP POLICY IF EXISTS "Users can view own analyses" ON analyses;')
    op.execute('DROP POLICY IF EXISTS "Users can create own analyses" ON analyses;')
    op.execute('DROP POLICY IF EXISTS "Users can update own analyses" ON analyses;')
    op.execute('DROP POLICY IF EXISTS "Users can delete own analyses" ON analyses;')
    
    # Refresh tokens table
    op.execute('DROP POLICY IF EXISTS "Users can view own refresh tokens" ON refresh_tokens;')
    op.execute('DROP POLICY IF EXISTS "Users can create own refresh tokens" ON refresh_tokens;')
    op.execute('DROP POLICY IF EXISTS "Users can delete own refresh tokens" ON refresh_tokens;')
    op.execute('DROP POLICY IF EXISTS "Users can update own refresh tokens" ON refresh_tokens;')
    
    # Disable RLS on all tables
    op.execute('ALTER TABLE members DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE analyses DISABLE ROW LEVEL SECURITY;')
    op.execute('ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY;')