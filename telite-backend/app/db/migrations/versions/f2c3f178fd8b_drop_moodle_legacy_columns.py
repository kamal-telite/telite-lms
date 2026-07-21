"""drop_moodle_legacy_columns

Revision ID: f2c3f178fd8b
Revises: a7330d0e2f3f
Create Date: 2026-07-21 07:27:56.410714

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c3f178fd8b'
down_revision: Union[str, None] = 'a7330d0e2f3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_course_modules_moodle_cmid'), table_name='course_modules', if_exists=True)
    
    # Drop columns
    op.drop_column('categories', 'moodle_category_id')
    op.drop_column('courses', 'moodle_course_id')
    op.drop_column('course_modules', 'moodle_cmid')
    op.drop_column('organizations', 'moodle_category_id')
    op.drop_column('organizations', 'moodle_tenant_key')
    op.drop_column('pal_quiz_scores', 'synced_from_moodle')
    op.drop_column('pending_verifications', 'moodle_id')
    op.drop_column('users', 'moodle_id')


def downgrade() -> None:
    op.add_column('users', sa.Column('moodle_id', sa.Integer(), nullable=True))
    op.add_column('pending_verifications', sa.Column('moodle_id', sa.Integer(), nullable=True))
    op.add_column('pal_quiz_scores', sa.Column('synced_from_moodle', sa.Integer(), server_default='0', nullable=False))
    op.add_column('organizations', sa.Column('moodle_tenant_key', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('moodle_category_id', sa.Integer(), nullable=True))
    op.add_column('course_modules', sa.Column('moodle_cmid', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('moodle_course_id', sa.Integer(), nullable=True))
    op.add_column('categories', sa.Column('moodle_category_id', sa.Integer(), nullable=True))

    op.create_index(op.f('ix_course_modules_moodle_cmid'), 'course_modules', ['moodle_cmid'], unique=False)
