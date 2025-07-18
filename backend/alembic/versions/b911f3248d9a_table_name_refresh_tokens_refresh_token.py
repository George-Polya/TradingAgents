"""table_name refresh_tokens -> refresh_token

Revision ID: b911f3248d9a
Revises: dc9d3583c30a
Create Date: 2025-07-16 19:20:26.079760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b911f3248d9a'
down_revision: Union[str, None] = 'dc9d3583c30a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
