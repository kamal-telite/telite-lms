"""drop obsolete section_progress table

Revision ID: 2eda72aef2a4
Revises: f8d0294cf280
Create Date: 2026-07-24 10:58:34.668378

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2eda72aef2a4'
down_revision: Union[str, None] = 'f8d0294cf280'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Idempotency Check
    if not inspector.has_table('section_progress'):
        print("Table 'section_progress' does not exist. Skipping drop.")
        return

    # 2. Production Safety Check
    result = conn.execute(sa.text("SELECT COUNT(*) FROM section_progress;"))
    row_count = result.scalar()
    
    print(f"Audit: Found {row_count} rows in 'section_progress'.")
    
    if row_count > 0:
        import os
        if os.environ.get("ALLOW_DROP_POPULATED_LEGACY_TABLES") != "1":
            raise RuntimeError(
                f"ABORTING MIGRATION: Table 'section_progress' contains {row_count} legacy rows.\n"
                "This table is obsolete and inaccessible from the new progression architecture.\n"
                "To permanently delete this dark data, run the migration with:\n"
                "ALLOW_DROP_POPULATED_LEGACY_TABLES=1 alembic upgrade head\n"
                "Otherwise, take a manual pg_dump of the table before proceeding."
            )
        else:
            print("WARNING: Operator explicitly authorized deletion of populated legacy table.")

    # 3. Drop Table
    op.drop_index(op.f('ix_section_progress_org_id'), table_name='section_progress')
    op.drop_index(op.f('ix_section_progress_section_id'), table_name='section_progress')
    op.drop_index(op.f('ix_section_progress_user_id'), table_name='section_progress')
    op.drop_table('section_progress')


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('section_progress'):
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
        sa.Column('time_spent_seconds', sa.Integer(), nullable=False, server_default='0', comment='Total time spent in section in seconds'),
        sa.Column('last_entered_at', sa.DateTime(timezone=True), nullable=True, comment='Last time learner entered the section'),
        sa.Column('last_left_at', sa.DateTime(timezone=True), nullable=True, comment='Last time learner left the section'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['course_sections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_section_progress_org_id'), 'section_progress', ['org_id'], unique=False)
    op.create_index(op.f('ix_section_progress_section_id'), 'section_progress', ['section_id'], unique=False)
    op.create_index(op.f('ix_section_progress_user_id'), 'section_progress', ['user_id'], unique=False)
