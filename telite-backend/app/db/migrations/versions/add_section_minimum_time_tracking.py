"""add_section_minimum_time_tracking

Revision ID: add_section_minimum_time_tracking
Revises: add_section_progress
Create Date: 2026-07-19 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'sec_time_001'
down_revision: Union[str, None] = 'add_section_progress'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Add minimum_time_seconds to course_sections table
    if 'course_sections' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('course_sections')]
        if 'minimum_time_seconds' not in columns:
            with op.batch_alter_table('course_sections', schema=None) as batch_op:
                batch_op.add_column(sa.Column('minimum_time_seconds', sa.Integer(), nullable=False, server_default='0', comment='Minimum required learning time in seconds'))
    
    # Add time tracking fields to section_progress table
    if 'section_progress' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('section_progress')]
        with op.batch_alter_table('section_progress', schema=None) as batch_op:
            if 'time_spent_seconds' not in columns:
                batch_op.add_column(sa.Column('time_spent_seconds', sa.Integer(), nullable=False, server_default='0', comment='Total time spent in section in seconds'))
            if 'last_entered_at' not in columns:
                batch_op.add_column(sa.Column('last_entered_at', sa.DateTime(timezone=True), nullable=True, comment='Last time learner entered the section'))
            if 'last_left_at' not in columns:
                batch_op.add_column(sa.Column('last_left_at', sa.DateTime(timezone=True), nullable=True, comment='Last time learner left the section'))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Remove minimum_time_seconds from course_sections table
    if 'course_sections' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('course_sections')]
        if 'minimum_time_seconds' in columns:
            with op.batch_alter_table('course_sections', schema=None) as batch_op:
                batch_op.drop_column('minimum_time_seconds')
    
    # Remove time tracking fields from section_progress table
    if 'section_progress' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('section_progress')]
        with op.batch_alter_table('section_progress', schema=None) as batch_op:
            if 'time_spent_seconds' in columns:
                batch_op.drop_column('time_spent_seconds')
            if 'last_entered_at' in columns:
                batch_op.drop_column('last_entered_at')
            if 'last_left_at' in columns:
                batch_op.drop_column('last_left_at')
