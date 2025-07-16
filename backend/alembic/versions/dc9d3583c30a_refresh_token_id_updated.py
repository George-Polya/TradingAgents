"""refresh_token id updated

Revision ID: dc9d3583c30a
Revises: 123f6236e005
Create Date: 2025-07-16 19:16:13.527524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc9d3583c30a'
down_revision: Union[str, None] = '123f6236e005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
