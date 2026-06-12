"""phase_f_progress_models

Revision ID: e40fc4255652
Revises: c2ea96aea04a
Create Date: 2026-06-08 10:33:12.075109

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e40fc4255652'
down_revision: Union[str, None] = 'c2ea96aea04a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create course_progress
    op.create_table('course_progress',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, comment='not_started, in_progress, completed'),
    sa.Column('completion_percentage', sa.Float(), nullable=False),
    sa.Column('time_spent_seconds', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('course_progress', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_course_progress_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_course_progress_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_course_progress_user_id'), ['user_id'], unique=False)

    # 2. Create learner_activity_log
    op.create_table('learner_activity_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.String(length=50), nullable=False),
    sa.Column('details', sa.String(length=500), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('learner_activity_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learner_activity_log_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_activity_log_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_activity_log_user_id'), ['user_id'], unique=False)

    # 3. Create learning_path_progress
    op.create_table('learning_path_progress',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('path_id', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, comment='not_started, in_progress, completed'),
    sa.Column('completion_percentage', sa.Float(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['path_id'], ['learning_paths.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('learning_path_progress', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learning_path_progress_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learning_path_progress_path_id'), ['path_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learning_path_progress_user_id'), ['user_id'], unique=False)

    # 4. Create learner_events
    op.create_table('learner_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=True),
    sa.Column('module_id', sa.Integer(), nullable=True),
    sa.Column('block_id', sa.String(length=50), nullable=True),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('schema_version', sa.String(length=10), nullable=False),
    sa.Column('payload_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.ForeignKeyConstraint(['block_id'], ['lesson_blocks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('learner_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_learner_events_block_id'), ['block_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_events_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_events_event_type'), ['event_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_events_module_id'), ['module_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_events_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_learner_events_user_id'), ['user_id'], unique=False)

    # 5. Create lesson_block_progress
    op.create_table('lesson_block_progress',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('block_id', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, comment='not_started, completed'),
    sa.Column('video_position_seconds', sa.Integer(), nullable=False, comment='Resume position for video blocks'),
    sa.Column('completion_percentage', sa.Float(), nullable=False),
    sa.Column('time_spent_seconds', sa.Integer(), nullable=False),
    sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['block_id'], ['lesson_blocks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('lesson_block_progress', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lesson_block_progress_block_id'), ['block_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lesson_block_progress_module_id'), ['module_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lesson_block_progress_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_lesson_block_progress_user_id'), ['user_id'], unique=False)

    # 6. Alter module_progress
    with op.batch_alter_table('module_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_block_id', sa.String(length=50), nullable=True, comment='For exact resume position'))
        batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('module_progress', schema=None) as batch_op:
        batch_op.drop_column('last_viewed_at')
        batch_op.drop_column('started_at')
        batch_op.drop_column('last_block_id')

    op.drop_table('lesson_block_progress')
    op.drop_table('learner_events')
    op.drop_table('learning_path_progress')
    op.drop_table('learner_activity_log')
    op.drop_table('course_progress')
