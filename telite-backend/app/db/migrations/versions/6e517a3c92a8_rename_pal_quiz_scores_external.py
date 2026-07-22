"""Rename pal_quiz_scores course_id to external_course_id

Revision ID: 6e517a3c92a8
Revises: f2c3f178fd8b
Create Date: 2026-07-22 22:38:48.123456

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6e517a3c92a8'
down_revision = 'ae9c5f8aaa97'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Rename the column
    op.execute("ALTER TABLE pal_quiz_scores RENAME COLUMN course_id TO external_course_id")
    # Rename the index
    op.execute("ALTER INDEX IF EXISTS ix_pal_quiz_scores_course_id RENAME TO ix_pal_quiz_scores_external_course_id")

def downgrade() -> None:
    # Revert index rename
    op.execute("ALTER INDEX IF EXISTS ix_pal_quiz_scores_external_course_id RENAME TO ix_pal_quiz_scores_course_id")
    # Revert column rename
    op.execute("ALTER TABLE pal_quiz_scores RENAME COLUMN external_course_id TO course_id")
