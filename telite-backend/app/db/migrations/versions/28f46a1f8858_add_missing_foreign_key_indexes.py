"""add_missing_foreign_key_indexes

Revision ID: 28f46a1f8858
Revises: task_gen_20260731
Create Date: 2026-08-01 02:03:11.405506

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f46a1f8858'
down_revision: Union[str, None] = 'task_gen_20260731'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing indexes to foreign keys for production performance optimization
    # Using if_not_exists=True to avoid conflicts with existing indexes
    
    # allowed_domain.py
    op.create_index('ix_allowed_domains_org_id', 'allowed_domains', ['org_id'], unique=False, if_not_exists=True)
    
    # assignment_submission.py
    op.create_index('ix_assignment_submissions_graded_by', 'assignment_submissions', ['graded_by'], unique=False, if_not_exists=True)
    op.create_index('ix_assignment_submissions_reviewed_by', 'assignment_submissions', ['reviewed_by'], unique=False, if_not_exists=True)
    
    # category.py
    op.create_index('ix_categories_organization_id', 'categories', ['organization_id'], unique=False, if_not_exists=True)
    
    # course_module.py
    op.create_index('ix_course_modules_section_id', 'course_modules', ['section_id'], unique=False, if_not_exists=True)
    op.create_index('ix_course_modules_deleted_by', 'course_modules', ['deleted_by'], unique=False, if_not_exists=True)
    
    # course_section.py
    op.create_index('ix_course_sections_deleted_by', 'course_sections', ['deleted_by'], unique=False, if_not_exists=True)
    
    # course_version.py
    op.create_index('ix_course_versions_course_id', 'course_versions', ['course_id'], unique=False, if_not_exists=True)
    op.create_index('ix_course_versions_parent_version_id', 'course_versions', ['parent_version_id'], unique=False, if_not_exists=True)
    op.create_index('ix_course_versions_published_by', 'course_versions', ['published_by'], unique=False, if_not_exists=True)
    op.create_index('ix_course_versions_created_by', 'course_versions', ['created_by'], unique=False, if_not_exists=True)
    
    # gradebook.py
    op.create_index('ix_grading_schemes_updated_by', 'grading_schemes', ['updated_by'], unique=False, if_not_exists=True)
    op.create_index('ix_grade_categories_updated_by', 'grade_categories', ['updated_by'], unique=False, if_not_exists=True)
    op.create_index('ix_grade_items_updated_by', 'grade_items', ['updated_by'], unique=False, if_not_exists=True)
    op.create_index('ix_grade_results_graded_by', 'grade_results', ['graded_by'], unique=False, if_not_exists=True)
    op.create_index('ix_course_grades_override_by', 'course_grades', ['override_by'], unique=False, if_not_exists=True)
    op.create_index('ix_completion_rules_updated_by', 'completion_rules', ['updated_by'], unique=False, if_not_exists=True)
    
    # invitation.py
    op.create_index('ix_org_invitations_org_id', 'org_invitations', ['org_id'], unique=False, if_not_exists=True)
    
    # learning_path.py
    op.create_index('ix_learning_paths_deleted_by', 'learning_paths', ['deleted_by'], unique=False, if_not_exists=True)
    
    # lesson_block.py
    op.create_index('ix_lesson_blocks_media_asset_id', 'lesson_blocks', ['media_asset_id'], unique=False, if_not_exists=True)
    op.create_index('ix_lesson_blocks_deleted_by', 'lesson_blocks', ['deleted_by'], unique=False, if_not_exists=True)
    
    # media_asset.py
    op.create_index('ix_media_assets_uploaded_by', 'media_assets', ['uploaded_by'], unique=False, if_not_exists=True)
    op.create_index('ix_media_assets_deleted_by', 'media_assets', ['deleted_by'], unique=False, if_not_exists=True)
    
    # pal.py - Note: PalTopicPerformance.user_id is not a foreign key, so no index needed
    
    # password_reset_token.py
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'], unique=False, if_not_exists=True)
    op.create_index('ix_password_reset_tokens_org_id', 'password_reset_tokens', ['org_id'], unique=False, if_not_exists=True)
    
    # progression_rule.py
    op.create_index('ix_progression_rules_created_by', 'progression_rules', ['created_by'], unique=False, if_not_exists=True)
    op.create_index('ix_progression_rules_updated_by', 'progression_rules', ['updated_by'], unique=False, if_not_exists=True)
    
    # question.py
    op.create_index('ix_questions_current_draft_version_id', 'questions', ['current_draft_version_id'], unique=False, if_not_exists=True)
    op.create_index('ix_questions_current_published_version_id', 'questions', ['current_published_version_id'], unique=False, if_not_exists=True)
    
    # question_bank.py
    op.create_index('ix_question_banks_deleted_by', 'question_banks', ['deleted_by'], unique=False, if_not_exists=True)
    
    # question_import_job.py
    op.create_index('ix_question_import_jobs_user_id', 'question_import_jobs', ['user_id'], unique=False, if_not_exists=True)
    
    # quiz_answer.py
    op.create_index('ix_quiz_answers_question_version_id', 'quiz_answers', ['question_version_id'], unique=False, if_not_exists=True)
    op.create_index('ix_grading_events_grader_id', 'grading_events', ['grader_id'], unique=False, if_not_exists=True)
    
    # quiz_attempt.py
    op.create_index('ix_quiz_attempt_questions_question_version_id', 'quiz_attempt_questions', ['question_version_id'], unique=False, if_not_exists=True)
    
    # quiz_models.py
    op.create_index('ix_quiz_definitions_deleted_by', 'quiz_definitions', ['deleted_by'], unique=False, if_not_exists=True)


def downgrade() -> None:
    # Remove the indexes added in upgrade
    # Using if_exists=True to avoid errors if indexes don't exist
    
    # allowed_domain.py
    op.drop_index('ix_allowed_domains_org_id', 'allowed_domains', if_exists=True)
    
    # assignment_submission.py
    op.drop_index('ix_assignment_submissions_graded_by', 'assignment_submissions', if_exists=True)
    op.drop_index('ix_assignment_submissions_reviewed_by', 'assignment_submissions', if_exists=True)
    
    # category.py
    op.drop_index('ix_categories_organization_id', 'categories', if_exists=True)
    
    # course_module.py
    op.drop_index('ix_course_modules_section_id', 'course_modules', if_exists=True)
    op.drop_index('ix_course_modules_deleted_by', 'course_modules', if_exists=True)
    
    # course_section.py
    op.drop_index('ix_course_sections_deleted_by', 'course_sections', if_exists=True)
    
    # course_version.py
    op.drop_index('ix_course_versions_course_id', 'course_versions', if_exists=True)
    op.drop_index('ix_course_versions_parent_version_id', 'course_versions', if_exists=True)
    op.drop_index('ix_course_versions_published_by', 'course_versions', if_exists=True)
    op.drop_index('ix_course_versions_created_by', 'course_versions', if_exists=True)
    
    # gradebook.py
    op.drop_index('ix_grading_schemes_updated_by', 'grading_schemes', if_exists=True)
    op.drop_index('ix_grade_categories_updated_by', 'grade_categories', if_exists=True)
    op.drop_index('ix_grade_items_updated_by', 'grade_items', if_exists=True)
    op.drop_index('ix_grade_results_graded_by', 'grade_results', if_exists=True)
    op.drop_index('ix_course_grades_override_by', 'course_grades', if_exists=True)
    op.drop_index('ix_completion_rules_updated_by', 'completion_rules', if_exists=True)
    
    # invitation.py
    op.drop_index('ix_org_invitations_org_id', 'org_invitations', if_exists=True)
    
    # learning_path.py
    op.drop_index('ix_learning_paths_deleted_by', 'learning_paths', if_exists=True)
    
    # lesson_block.py
    op.drop_index('ix_lesson_blocks_media_asset_id', 'lesson_blocks', if_exists=True)
    op.drop_index('ix_lesson_blocks_deleted_by', 'lesson_blocks', if_exists=True)
    
    # media_asset.py
    op.drop_index('ix_media_assets_uploaded_by', 'media_assets', if_exists=True)
    op.drop_index('ix_media_assets_deleted_by', 'media_assets', if_exists=True)
    
    # pal.py - Note: PalTopicPerformance.user_id is not a foreign key, so no index needed
    
    # password_reset_token.py
    op.drop_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', if_exists=True)
    op.drop_index('ix_password_reset_tokens_org_id', 'password_reset_tokens', if_exists=True)
    
    # progression_rule.py
    op.drop_index('ix_progression_rules_created_by', 'progression_rules', if_exists=True)
    op.drop_index('ix_progression_rules_updated_by', 'progression_rules', if_exists=True)
    
    # question.py
    op.drop_index('ix_questions_current_draft_version_id', 'questions', if_exists=True)
    op.drop_index('ix_questions_current_published_version_id', 'questions', if_exists=True)
    
    # question_bank.py
    op.drop_index('ix_question_banks_deleted_by', 'question_banks', if_exists=True)
    
    # question_import_job.py
    op.drop_index('ix_question_import_jobs_user_id', 'question_import_jobs', if_exists=True)
    
    # quiz_answer.py
    op.drop_index('ix_quiz_answers_question_version_id', 'quiz_answers', if_exists=True)
    op.drop_index('ix_grading_events_grader_id', 'grading_events', if_exists=True)
    
    # quiz_attempt.py
    op.drop_index('ix_quiz_attempt_questions_question_version_id', 'quiz_attempt_questions', if_exists=True)
    
    # quiz_models.py
    op.drop_index('ix_quiz_definitions_deleted_by', 'quiz_definitions', if_exists=True)
