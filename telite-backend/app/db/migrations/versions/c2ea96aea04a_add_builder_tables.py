"""add_builder_tables

Revision ID: c2ea96aea04a
Revises: db5ba62f5025
Create Date: 2026-06-08 02:36:44.501021

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2ea96aea04a'
down_revision: Union[str, None] = 'db5ba62f5025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('builder_activity_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('payload', sa.Text(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('builder_activity_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_builder_activity_log_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_builder_activity_log_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_builder_activity_log_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_builder_activity_log_user_id'), ['user_id'], unique=False)

    op.create_table('course_edit_locks',
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('course_id')
    )
    with op.batch_alter_table('course_edit_locks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_course_edit_locks_org_id'), ['org_id'], unique=False)


def downgrade() -> None:
    op.drop_table('course_edit_locks')
    op.drop_table('builder_activity_log')
