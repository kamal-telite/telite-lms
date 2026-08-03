"""add_safe_numeric_check_constraints_batch1

Revision ID: b558c017fe3a
Revises: c0231a8632a7
Create Date: 2026-08-01 17:10:38.523700

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b558c017fe3a'
down_revision: Union[str, None] = '262cdd79253b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CHECK constraint for course_progress.completion_percentage
    op.create_check_constraint(
        'chk_course_progress_completion_percentage',
        'course_progress',
        'completion_percentage >= 0 AND completion_percentage <= 100'
    )
    
    # Add CHECK constraint for course_progress.time_spent_seconds
    op.create_check_constraint(
        'chk_course_progress_time_spent_seconds',
        'course_progress',
        'time_spent_seconds >= 0'
    )
    
    # Add CHECK constraint for assignment_submissions.attempt_number
    op.create_check_constraint(
        'chk_assignment_submissions_attempt_number',
        'assignment_submissions',
        'attempt_number >= 1'
    )
    
    # Add CHECK constraint for assignment_submissions.course_progress_pct_at_submission
    op.create_check_constraint(
        'chk_assignment_submissions_course_progress_pct',
        'assignment_submissions',
        'course_progress_pct_at_submission >= 0 AND course_progress_pct_at_submission <= 100'
    )
    
    # Add CHECK constraint for question_versions.version_number
    op.create_check_constraint(
        'chk_question_versions_version_number',
        'question_versions',
        'version_number >= 1'
    )


def downgrade() -> None:
    # Remove CHECK constraint for course_progress.completion_percentage
    op.drop_constraint('chk_course_progress_completion_percentage', 'course_progress')
    
    # Remove CHECK constraint for course_progress.time_spent_seconds
    op.drop_constraint('chk_course_progress_time_spent_seconds', 'course_progress')
    
    # Remove CHECK constraint for assignment_submissions.attempt_number
    op.drop_constraint('chk_assignment_submissions_attempt_number', 'assignment_submissions')
    
    # Remove CHECK constraint for assignment_submissions.course_progress_pct_at_submission
    op.drop_constraint('chk_assignment_submissions_course_progress_pct', 'assignment_submissions')
    
    # Remove CHECK constraint for question_versions.version_number
    op.drop_constraint('chk_question_versions_version_number', 'question_versions')
