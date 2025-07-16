"""update_analyses_table_with_all_fields

Revision ID: f6g7h8i9j012
Revises: c12214f23ddf
Create Date: 2025-07-16 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j012'
down_revision: Union[str, None] = 'c12214f23ddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns first (without status)
    op.add_column('analyses', sa.Column('analysis_date', sa.Date(), nullable=False, server_default=sa.func.current_date()))
    op.add_column('analyses', sa.Column('analysts_selected', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('analyses', sa.Column('research_depth', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('analyses', sa.Column('llm_provider', sa.String(), nullable=False, server_default=''))
    op.add_column('analyses', sa.Column('backend_url', sa.String(), nullable=False, server_default=''))
    op.add_column('analyses', sa.Column('shallow_thinker', sa.String(), nullable=False, server_default=''))
    op.add_column('analyses', sa.Column('deep_thinker', sa.String(), nullable=False, server_default=''))
    
    # Add status column as string temporarily
    op.add_column('analyses', sa.Column('status', sa.String(), nullable=False, server_default='pending'))
    
    # Add report columns (all nullable)
    op.add_column('analyses', sa.Column('market_report', sa.Text(), nullable=True))
    op.add_column('analyses', sa.Column('news_report', sa.Text(), nullable=True))
    op.add_column('analyses', sa.Column('fundamentals_report', sa.Text(), nullable=True))
    
    # Add process state columns
    op.add_column('analyses', sa.Column('investment_debate_state', sa.JSON(), nullable=True))
    op.add_column('analyses', sa.Column('trader_investment_plan', sa.Text(), nullable=True))
    op.add_column('analyses', sa.Column('risk_debate_state', sa.JSON(), nullable=True))
    
    # Add final result columns
    op.add_column('analyses', sa.Column('final_trade_decision', sa.Text(), nullable=True))
    op.add_column('analyses', sa.Column('final_report', sa.Text(), nullable=True))
    
    # Add execution info columns
    op.add_column('analyses', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('analyses', sa.Column('completed_at', sa.DateTime(), nullable=True))
    
    # Drop unused columns
    op.drop_column('analyses', 'company_name')
    op.drop_column('analyses', 'result')


def downgrade() -> None:
    # Add back old columns
    op.add_column('analyses', sa.Column('company_name', sa.String(255), nullable=False, server_default=''))
    op.add_column('analyses', sa.Column('result', sa.Text(), nullable=True))
    
    # Drop new columns
    op.drop_column('analyses', 'completed_at')
    op.drop_column('analyses', 'error_message')
    op.drop_column('analyses', 'final_report')
    op.drop_column('analyses', 'final_trade_decision')
    op.drop_column('analyses', 'risk_debate_state')
    op.drop_column('analyses', 'trader_investment_plan')
    op.drop_column('analyses', 'investment_debate_state')
    op.drop_column('analyses', 'fundamentals_report')
    op.drop_column('analyses', 'news_report')
    op.drop_column('analyses', 'market_report')
    op.drop_column('analyses', 'status')
    op.drop_column('analyses', 'deep_thinker')
    op.drop_column('analyses', 'shallow_thinker')
    op.drop_column('analyses', 'backend_url')
    op.drop_column('analyses', 'llm_provider')
    op.drop_column('analyses', 'research_depth')
    op.drop_column('analyses', 'analysts_selected')
    op.drop_column('analyses', 'analysis_date')
    
    # Drop enum type
    analysis_status_enum = postgresql.ENUM('pending', 'running', 'completed', 'failed', 'cancelled', name='analysisstatus')
    analysis_status_enum.drop(op.get_bind())