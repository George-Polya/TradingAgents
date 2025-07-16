"""Change TEXT columns to LONGTEXT for analysis reports

Revision ID: 001
Revises: 
Create Date: 2025-07-07 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change TEXT columns to TEXT for PostgreSQL compatibility."""
    # In PostgreSQL, TEXT type already supports unlimited length, so this migration is a no-op
    pass


def downgrade() -> None:
    """Revert - no-op for PostgreSQL."""
    # In PostgreSQL, TEXT type already supports unlimited length, so this migration is a no-op
    pass