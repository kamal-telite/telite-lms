"""merge learning sessions and minimum time

Revision ID: 4cc311cff7e4
Revises: learning_sessions_20260707, add_section_minimum_time_tracking
Create Date: 2026-07-19 16:02:40.090744

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cc311cff7e4'
down_revision: Union[str, None] = ('learning_sessions_20260707', 'sec_time_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
