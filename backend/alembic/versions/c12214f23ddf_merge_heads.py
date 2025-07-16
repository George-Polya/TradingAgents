"""merge heads

Revision ID: c12214f23ddf
Revises: e5f6g7h8i901, b911f3248d9a
Create Date: 2025-07-16 19:24:53.049393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c12214f23ddf'
down_revision: Union[str, None] = ('e5f6g7h8i901', 'b911f3248d9a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
