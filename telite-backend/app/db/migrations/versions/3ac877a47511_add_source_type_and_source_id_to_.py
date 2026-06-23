"""add_source_type_and_source_id_to_notifications

Revision ID: 3ac877a47511
Revises: 57d2868d07e4
Create Date: 2026-06-21 23:15:55.322606

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3ac877a47511'
down_revision: Union[str, None] = '57d2868d07e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('source_id', sa.String(length=50), nullable=True))
        batch_op.create_index(batch_op.f('ix_notifications_source_id'), ['source_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_source_type'), ['source_type'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_source_type'))
        batch_op.drop_index(batch_op.f('ix_notifications_source_id'))
        batch_op.drop_column('source_id')
        batch_op.drop_column('source_type')
