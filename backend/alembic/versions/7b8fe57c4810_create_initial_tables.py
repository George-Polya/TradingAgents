"""create_initial_tables

Revision ID: 7b8fe57c4810
Revises: 
Create Date: 2025-07-16 10:15:12.268597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b8fe57c4810'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create members table
    op.create_table(
        'members',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('member_id', sa.String(36), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE')
    )
    
    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('member_id', sa.String(36), nullable=False),
        sa.Column('token', sa.String(500), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('idx_members_email', 'members', ['email'])
    op.create_index('idx_analyses_member_id', 'analyses', ['member_id'])
    op.create_index('idx_analyses_ticker', 'analyses', ['ticker'])
    op.create_index('idx_refresh_tokens_member_id', 'refresh_tokens', ['member_id'])
    op.create_index('idx_refresh_tokens_token', 'refresh_tokens', ['token'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_refresh_tokens_token', 'refresh_tokens')
    op.drop_index('idx_refresh_tokens_member_id', 'refresh_tokens')
    op.drop_index('idx_analyses_ticker', 'analyses')
    op.drop_index('idx_analyses_member_id', 'analyses')
    op.drop_index('idx_members_email', 'members')
    
    # Drop tables
    op.drop_table('refresh_tokens')
    op.drop_table('analyses')
    op.drop_table('members')
