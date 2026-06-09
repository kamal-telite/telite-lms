"""Add course module tables Phase B

Revision ID: 3ad32707e699
Revises: 001_phase3
Create Date: 2026-06-07 22:58:04.436045

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ad32707e699'
down_revision: Union[str, None] = '001_phase3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # course_modules table
    op.create_table('course_modules',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('moodle_cmid', sa.Integer(), nullable=True, comment='Moodle Course Module ID'),
    sa.Column('section', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('module_type', sa.String(length=50), nullable=False, comment='e.g. page, url, quiz, scorm'),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('content_url', sa.Text(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_modules_course_id'), 'course_modules', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_modules_moodle_cmid'), 'course_modules', ['moodle_cmid'], unique=False)
    op.create_index(op.f('ix_course_modules_org_id'), 'course_modules', ['org_id'], unique=False)
    
    # module_progress table
    op.create_table('module_progress',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, comment='not_started, in_progress, completed'),
    sa.Column('score', sa.Float(), nullable=True, comment='For quizzes/SCORM'),
    sa.Column('time_spent_seconds', sa.Integer(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_module_progress_module_id'), 'module_progress', ['module_id'], unique=False)
    op.create_index(op.f('ix_module_progress_org_id'), 'module_progress', ['org_id'], unique=False)
    op.create_index(op.f('ix_module_progress_user_id'), 'module_progress', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_module_progress_user_id'), table_name='module_progress')
    op.drop_index(op.f('ix_module_progress_org_id'), table_name='module_progress')
    op.drop_index(op.f('ix_module_progress_module_id'), table_name='module_progress')
    op.drop_table('module_progress')
    op.drop_index(op.f('ix_course_modules_org_id'), table_name='course_modules')
    op.drop_index(op.f('ix_course_modules_moodle_cmid'), table_name='course_modules')
    op.drop_index(op.f('ix_course_modules_course_id'), table_name='course_modules')
    op.drop_table('course_modules')
