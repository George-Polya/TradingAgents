"""drop_market_report_column

Revision ID: i9j0k1l2m345
Revises: h8i9j0k1l234
Create Date: 2025-07-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'i9j0k1l2m345'
down_revision: Union[str, None] = 'h8i9j0k1l234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop market_report column from analysis table
    op.drop_column('analysis', 'market_report')


def downgrade() -> None:
    # Re-add market_report column if rolling back
    op.add_column('analysis', 
        sa.Column('market_report', sa.Text(), nullable=True)
    )