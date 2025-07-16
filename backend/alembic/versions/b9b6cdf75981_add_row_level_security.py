"""add_row_level_security

Revision ID: b9b6cdf75981
Revises: 7b8fe57c4810
Create Date: 2025-07-16 10:15:58.036795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9b6cdf75981'
down_revision: Union[str, None] = '7b8fe57c4810'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable RLS on tables
    op.execute("ALTER TABLE members ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    
    # Create function to set user context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_current_user_context(user_id VARCHAR)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_user_id', user_id, false);
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # Create RLS policies for members table
    op.execute("""
        CREATE POLICY "Users can view own profile" ON members
        FOR SELECT USING (id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can update own profile" ON members
        FOR UPDATE USING (id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    # Create RLS policies for analyses table
    op.execute("""
        CREATE POLICY "Users can view own analyses" ON analyses
        FOR SELECT USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can create own analyses" ON analyses
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can update own analyses" ON analyses
        FOR UPDATE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can delete own analyses" ON analyses
        FOR DELETE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    # Create RLS policies for refresh_tokens table
    op.execute("""
        CREATE POLICY "Users can view own tokens" ON refresh_tokens
        FOR SELECT USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can create own tokens" ON refresh_tokens
        FOR INSERT WITH CHECK (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    op.execute("""
        CREATE POLICY "Users can delete own tokens" ON refresh_tokens
        FOR DELETE USING (member_id = current_setting('app.current_user_id', true)::VARCHAR)
    """)
    
    # Create helper functions for auth operations
    op.execute("""
        CREATE OR REPLACE FUNCTION create_user_with_rls(
            p_email VARCHAR,
            p_password VARCHAR,
            p_name VARCHAR
        )
        RETURNS TABLE(id VARCHAR, email VARCHAR, name VARCHAR) AS $$
        DECLARE
            v_user_id VARCHAR;
        BEGIN
            -- Insert user without RLS check
            INSERT INTO members (id, email, password, name)
            VALUES (gen_random_uuid()::VARCHAR, p_email, p_password, p_name)
            RETURNING members.id INTO v_user_id;
            
            -- Return user data
            RETURN QUERY
            SELECT m.id, m.email, m.name
            FROM members m
            WHERE m.id = v_user_id;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION verify_user_for_login(
            p_email VARCHAR
        )
        RETURNS TABLE(id VARCHAR, email VARCHAR, password VARCHAR, name VARCHAR) AS $$
        BEGIN
            RETURN QUERY
            SELECT m.id, m.email, m.password, m.name
            FROM members m
            WHERE m.email = p_email;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)


def downgrade() -> None:
    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS verify_user_for_login(VARCHAR)")
    op.execute("DROP FUNCTION IF EXISTS create_user_with_rls(VARCHAR, VARCHAR, VARCHAR)")
    
    # Drop RLS policies for refresh_tokens
    op.execute("DROP POLICY IF EXISTS \"Users can delete own tokens\" ON refresh_tokens")
    op.execute("DROP POLICY IF EXISTS \"Users can create own tokens\" ON refresh_tokens")
    op.execute("DROP POLICY IF EXISTS \"Users can view own tokens\" ON refresh_tokens")
    
    # Drop RLS policies for analyses
    op.execute("DROP POLICY IF EXISTS \"Users can delete own analyses\" ON analyses")
    op.execute("DROP POLICY IF EXISTS \"Users can update own analyses\" ON analyses")
    op.execute("DROP POLICY IF EXISTS \"Users can create own analyses\" ON analyses")
    op.execute("DROP POLICY IF EXISTS \"Users can view own analyses\" ON analyses")
    
    # Drop RLS policies for members
    op.execute("DROP POLICY IF EXISTS \"Users can update own profile\" ON members")
    op.execute("DROP POLICY IF EXISTS \"Users can view own profile\" ON members")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS set_current_user_context(VARCHAR)")
    
    # Disable RLS on tables
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE members DISABLE ROW LEVEL SECURITY")
