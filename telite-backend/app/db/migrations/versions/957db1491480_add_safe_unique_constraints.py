"""add_safe_unique_constraints

Revision ID: 957db1491480
Revises: 29a994d0afeb
Create Date: 2026-08-01 02:44:50.931502

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '957db1491480'
down_revision: Union[str, None] = '29a994d0afeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add safe unique constraints that match application-level duplicate prevention
    
    # QuizAnswer: (attempt_id, question_version_id)
    # Application already checks for duplicates before creating answers
    op.create_unique_constraint('uq_quiz_answers_attempt_question', 'quiz_answers', ['attempt_id', 'question_version_id'])
    
    # RolePermission: (org_id, role, permission_key)
    # Application already checks for duplicates before creating permission overrides
    op.create_unique_constraint('uq_role_permissions_org_role_permission', 'role_permissions', ['org_id', 'role', 'permission_key'])
    
    # QuizSettings: (quiz_id, org_id)
    # Application already ensures only one settings row per quiz per org
    op.create_unique_constraint('uq_quiz_settings_quiz_org', 'quiz_settings', ['quiz_id', 'org_id'])
    
    # QuestionVersion: (question_id, version_number)
    # Application now correctly increments version numbers (bug fixed)
    op.create_unique_constraint('uq_question_versions_question_version', 'question_versions', ['question_id', 'version_number'])


def downgrade() -> None:
    # Remove the safe unique constraints
    op.drop_constraint('uq_quiz_answers_attempt_question', 'quiz_answers')
    op.drop_constraint('uq_role_permissions_org_role_permission', 'role_permissions')
    op.drop_constraint('uq_quiz_settings_quiz_org', 'quiz_settings')
    op.drop_constraint('uq_question_versions_question_version', 'question_versions')
