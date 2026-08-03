"""add_composite_indexes_for_query_optimization

Revision ID: 29a994d0afeb
Revises: 28f46a1f8858
Create Date: 2026-08-01 02:23:02.918705

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29a994d0afeb'
down_revision: Union[str, None] = '28f46a1f8858'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite indexes for query optimization based on repository query patterns
    
    # Progress tracking indexes (HIGH PRIORITY - Core learning functionality)
    op.create_index('ix_course_progress_org_user_course_created', 'course_progress', ['org_id', 'user_id', 'course_id', 'created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_module_progress_org_user_module_created', 'module_progress', ['org_id', 'user_id', 'module_id', 'created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_section_progress_org_user_section_created', 'section_progress', ['org_id', 'user_id', 'section_id', 'created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_lesson_block_progress_org_user_block_created', 'lesson_block_progress', ['org_id', 'user_id', 'block_id', 'created_at'], unique=False, if_not_exists=True)
    
    # Enrollment management indexes (HIGH PRIORITY - Access control)
    op.create_index('ix_enrollment_requests_org_email_category', 'enrollment_requests', ['org_id', 'email', 'category_slug'], unique=False, if_not_exists=True)
    op.create_index('ix_enrollment_requests_org_status_category', 'enrollment_requests', ['org_id', 'status', 'category_slug'], unique=False, if_not_exists=True)
    
    # Notification indexes (HIGH PRIORITY - User experience)
    op.create_index('ix_notifications_org_user_created', 'notifications', ['org_id', 'user_id', 'created_at'], unique=False, if_not_exists=True)
    op.create_index('ix_notifications_org_user_read_created', 'notifications', ['org_id', 'user_id', 'is_read', 'created_at'], unique=False, if_not_exists=True)
    
    # User management indexes (HIGH PRIORITY - Admin functionality)
    op.create_index('ix_users_org_role_active', 'users', ['org_id', 'role', 'is_active'], unique=False, if_not_exists=True)
    
    # Course builder indexes (HIGH PRIORITY - Course structure)
    op.create_index('ix_course_sections_org_course_deleted_sort', 'course_sections', ['org_id', 'course_id', 'deleted_at', 'sort_order'], unique=False, if_not_exists=True)
    op.create_index('ix_course_modules_org_course_deleted_sort', 'course_modules', ['org_id', 'course_id', 'deleted_at', 'sort_order'], unique=False, if_not_exists=True)
    op.create_index('ix_lesson_blocks_org_module_deleted_sort', 'lesson_blocks', ['org_id', 'module_id', 'deleted_at', 'sort_order'], unique=False, if_not_exists=True)
    
    # Assignment indexes (HIGH PRIORITY - Grading workflow)
    op.create_index('ix_assignment_submissions_org_block_user', 'assignment_submissions', ['org_id', 'block_id', 'user_id'], unique=False, if_not_exists=True)
    
    # Learning path indexes (HIGH PRIORITY - Path tracking)
    op.create_index('ix_learning_path_progress_org_user_path', 'learning_path_progress', ['org_id', 'user_id', 'path_id'], unique=False, if_not_exists=True)
    
    # Announcement indexes (MEDIUM PRIORITY - Admin dashboard)
    op.create_index('ix_announcements_org_created', 'announcements', ['org_id', 'created_at'], unique=False, if_not_exists=True)
    
    # Course listing indexes (HIGH PRIORITY - Course browsing)
    op.create_index('ix_courses_org_category_status', 'courses', ['org_id', 'category_slug', 'status'], unique=False, if_not_exists=True)


def downgrade() -> None:
    # Remove the composite indexes added in upgrade
    op.drop_index('ix_course_progress_org_user_course_created', 'course_progress', if_exists=True)
    op.drop_index('ix_module_progress_org_user_module_created', 'module_progress', if_exists=True)
    op.drop_index('ix_section_progress_org_user_section_created', 'section_progress', if_exists=True)
    op.drop_index('ix_lesson_block_progress_org_user_block_created', 'lesson_block_progress', if_exists=True)
    op.drop_index('ix_enrollment_requests_org_email_category', 'enrollment_requests', if_exists=True)
    op.drop_index('ix_enrollment_requests_org_status_category', 'enrollment_requests', if_exists=True)
    op.drop_index('ix_notifications_org_user_created', 'notifications', if_exists=True)
    op.drop_index('ix_notifications_org_user_read_created', 'notifications', if_exists=True)
    op.drop_index('ix_users_org_role_active', 'users', if_exists=True)
    op.drop_index('ix_course_sections_org_course_deleted_sort', 'course_sections', if_exists=True)
    op.drop_index('ix_course_modules_org_course_deleted_sort', 'course_modules', if_exists=True)
    op.drop_index('ix_lesson_blocks_org_module_deleted_sort', 'lesson_blocks', if_exists=True)
    op.drop_index('ix_assignment_submissions_org_block_user', 'assignment_submissions', if_exists=True)
    op.drop_index('ix_learning_path_progress_org_user_path', 'learning_path_progress', if_exists=True)
    op.drop_index('ix_announcements_org_created', 'announcements', if_exists=True)
    op.drop_index('ix_courses_org_category_status', 'courses', if_exists=True)
