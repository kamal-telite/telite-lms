"""drop obsolete quiz_questions table

Revision ID: f8d0294cf280
Revises: bc3094830c04
Create Date: 2026-07-24 10:45:10.398426

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8d0294cf280'
down_revision: Union[str, None] = 'bc3094830c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Idempotency Check: Check if table exists
    if not inspector.has_table('quiz_questions'):
        print("Table 'quiz_questions' does not exist. Skipping drop.")
        return

    # 2. Production Safety Check: Check for legacy data
    result = conn.execute(sa.text("SELECT COUNT(*) FROM quiz_questions;"))
    row_count = result.scalar()
    
    print(f"Audit: Found {row_count} rows in 'quiz_questions'.")
    
    if row_count > 0:
        # Require explicit override via environment variable if data exists
        import os
        if os.environ.get("ALLOW_DROP_POPULATED_QUIZ_QUESTIONS") != "1":
            raise RuntimeError(
                f"ABORTING MIGRATION: Table 'quiz_questions' contains {row_count} legacy rows.\n"
                "This table is obsolete and inaccessible from the Phase D architecture.\n"
                "To permanently delete this dark data, run the migration with:\n"
                "ALLOW_DROP_POPULATED_QUIZ_QUESTIONS=1 alembic upgrade head\n"
                "Otherwise, take a manual pg_dump of the table before proceeding."
            )
        else:
            print("WARNING: Operator explicitly authorized deletion of populated legacy table.")

    # 3. Drop Table (Indexes drop automatically, but we drop them explicitly for completeness)
    op.drop_index(op.f('ix_quiz_questions_quiz_id'), table_name='quiz_questions')
    op.drop_index(op.f('ix_quiz_questions_org_id'), table_name='quiz_questions')
    op.drop_index(op.f('ix_quiz_questions_id'), table_name='quiz_questions')
    op.drop_table('quiz_questions')


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('quiz_questions'):
        return

    op.create_table('quiz_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options_json', sa.JSON(), nullable=True),
        sa.Column('correct_answer_json', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['quiz_id'], ['quiz_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_id'), 'quiz_questions', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_questions_org_id'), 'quiz_questions', ['org_id'], unique=False)
    op.create_index(op.f('ix_quiz_questions_quiz_id'), 'quiz_questions', ['quiz_id'], unique=False)
