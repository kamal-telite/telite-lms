"""add_safe_numeric_check_constraints_batch2_course

Revision ID: 82a9a3f48a00
Revises: b558c017fe3a
Create Date: 2026-08-01 17:25:19.596911

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82a9a3f48a00'
down_revision: Union[str, None] = 'b558c017fe3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CHECK constraint for courses.module_count
    op.create_check_constraint(
        'chk_courses_module_count',
        'courses',
        'module_count >= 0'
    )
    
    # Add CHECK constraint for courses.lessons_count
    op.create_check_constraint(
        'chk_courses_lessons_count',
        'courses',
        'lessons_count >= 0'
    )
    
    # Add CHECK constraint for courses.hours
    op.create_check_constraint(
        'chk_courses_hours',
        'courses',
        'hours >= 0'
    )
    
    # Add CHECK constraint for courses.enrolled_count
    op.create_check_constraint(
        'chk_courses_enrolled_count',
        'courses',
        'enrolled_count >= 0'
    )
    
    # Add CHECK constraint for courses.completion_count
    op.create_check_constraint(
        'chk_courses_completion_count',
        'courses',
        'completion_count >= 0'
    )
    
    # Add CHECK constraint for courses.completion_rate
    op.create_check_constraint(
        'chk_courses_completion_rate',
        'courses',
        'completion_rate >= 0 AND completion_rate <= 100'
    )
    
    # Add CHECK constraint for courses.avg_quiz_score
    op.create_check_constraint(
        'chk_courses_avg_quiz_score',
        'courses',
        'avg_quiz_score >= 0 AND avg_quiz_score <= 100'
    )
    
    # Add CHECK constraint for courses.price_paise
    op.create_check_constraint(
        'chk_courses_price_paise',
        'courses',
        'price_paise >= 0'
    )


def downgrade() -> None:
    # Remove CHECK constraint for courses.module_count
    op.drop_constraint('chk_courses_module_count', 'courses')
    
    # Remove CHECK constraint for courses.lessons_count
    op.drop_constraint('chk_courses_lessons_count', 'courses')
    
    # Remove CHECK constraint for courses.hours
    op.drop_constraint('chk_courses_hours', 'courses')
    
    # Remove CHECK constraint for courses.enrolled_count
    op.drop_constraint('chk_courses_enrolled_count', 'courses')
    
    # Remove CHECK constraint for courses.completion_count
    op.drop_constraint('chk_courses_completion_count', 'courses')
    
    # Remove CHECK constraint for courses.completion_rate
    op.drop_constraint('chk_courses_completion_rate', 'courses')
    
    # Remove CHECK constraint for courses.avg_quiz_score
    op.drop_constraint('chk_courses_avg_quiz_score', 'courses')
    
    # Remove CHECK constraint for courses.price_paise
    op.drop_constraint('chk_courses_price_paise', 'courses')
