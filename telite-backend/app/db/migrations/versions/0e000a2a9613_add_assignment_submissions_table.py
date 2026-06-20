"""add_assignment_submissions_table

Revision ID: 0e000a2a9613
Revises: c1669e51aea9
Create Date: 2026-06-17 15:12:32.199002

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0e000a2a9613'
down_revision: Union[str, None] = 'c1669e51aea9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.engine.reflection import Inspector

def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    if 'assignment_submissions' not in tables:
        op.create_table(
            'assignment_submissions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('block_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=50), nullable=False),
            sa.Column('org_id', sa.Integer(), nullable=False),
            sa.Column('submission_text', sa.Text(), nullable=True),
            sa.Column('submission_files_json', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='submitted'),
            sa.Column('grade', sa.Float(), nullable=True),
            sa.Column('feedback', sa.Text(), nullable=True),
            sa.Column('graded_by', sa.String(length=50), nullable=True),
            sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['block_id'], ['lesson_blocks.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['graded_by'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('block_id', 'user_id', name='uq_assignment_submission_block_user')
        )
        op.create_index(op.f('ix_assignment_submissions_block_id'), 'assignment_submissions', ['block_id'], unique=False)
        op.create_index(op.f('ix_assignment_submissions_org_id'), 'assignment_submissions', ['org_id'], unique=False)
        op.create_index(op.f('ix_assignment_submissions_status'), 'assignment_submissions', ['status'], unique=False)
        op.create_index(op.f('ix_assignment_submissions_user_id'), 'assignment_submissions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_assignment_submissions_user_id'), table_name='assignment_submissions')
    op.drop_index(op.f('ix_assignment_submissions_status'), table_name='assignment_submissions')
    op.drop_index(op.f('ix_assignment_submissions_org_id'), table_name='assignment_submissions')
    op.drop_index(op.f('ix_assignment_submissions_block_id'), table_name='assignment_submissions')
    op.drop_table('assignment_submissions')
