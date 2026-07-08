"""add_section_progress

Revision ID: add_section_progress
Revises: h1e2f3g4h5i6
Create Date: 2026-06-30 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'add_section_progress'
down_revision: Union[str, None] = 'h1e2f3g4h5i6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if 'section_progress' in inspector.get_table_names():
        return

    op.create_table('section_progress',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.String(length=50), nullable=False),
    sa.Column('section_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False, server_default='not_started', comment='not_started, in_progress, completed'),
    sa.Column('completion_percentage', sa.Float(), nullable=False, server_default='0.0'),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=False, comment='Tenant organisation ID — used by RLS policies'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['section_id'], ['course_sections.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('section_progress', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_section_progress_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_section_progress_section_id'), ['section_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_section_progress_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if 'section_progress' in inspector.get_table_names():
        op.drop_table('section_progress')
