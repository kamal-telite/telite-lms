"""phase_c_native_course_builder

Revision ID: 417f828b3e0a
Revises: 3ad32707e699
Create Date: 2026-06-07 23:30:45.574840

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '417f828b3e0a'
down_revision: Union[str, None] = '3ad32707e699'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('course_sections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_sections_course_id'), 'course_sections', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_sections_id'), 'course_sections', ['id'], unique=False)
    op.create_index(op.f('ix_course_sections_org_id'), 'course_sections', ['org_id'], unique=False)
    op.create_table('course_versions',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('parent_version_id', sa.String(length=50), nullable=True),
    sa.Column('created_by', sa.String(length=50), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('published_by', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['parent_version_id'], ['course_versions.id'], ),
    sa.ForeignKeyConstraint(['published_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_course_versions_course_id'), 'course_versions', ['course_id'], unique=False)
    op.create_index(op.f('ix_course_versions_org_id'), 'course_versions', ['org_id'], unique=False)
    op.create_index(op.f('ix_course_versions_status'), 'course_versions', ['status'], unique=False)
    op.create_table('learning_paths',
    sa.Column('id', sa.String(length=50), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_paths_org_id'), 'learning_paths', ['org_id'], unique=False)
    op.create_index(op.f('ix_learning_paths_status'), 'learning_paths', ['status'], unique=False)
    op.create_table('media_assets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.String(length=50), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('file_type', sa.String(length=50), nullable=False),
    sa.Column('file_size', sa.Integer(), nullable=False),
    sa.Column('storage_key', sa.String(length=255), nullable=False),
    sa.Column('storage_provider', sa.String(length=50), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_assets_id'), 'media_assets', ['id'], unique=False)
    op.create_index(op.f('ix_media_assets_org_id'), 'media_assets', ['org_id'], unique=False)
    op.create_table('learning_path_courses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('learning_path_id', sa.String(length=50), nullable=False),
    sa.Column('course_id', sa.String(length=50), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_mandatory', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_path_courses_id'), 'learning_path_courses', ['id'], unique=False)
    
    with op.batch_alter_table('course_modules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('section_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='published'))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('deleted_by', sa.String(length=50), nullable=True))
        batch_op.create_foreign_key('fk_course_modules_section_id', 'course_sections', ['section_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_course_modules_deleted_by', 'users', ['deleted_by'], ['id'])

    op.create_table('lesson_blocks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('block_type', sa.String(length=50), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('media_asset_id', sa.Integer(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('metadata_json', sa.JSON(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['media_asset_id'], ['media_assets.id'], ),
    sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lesson_blocks_id'), 'lesson_blocks', ['id'], unique=False)
    op.create_index(op.f('ix_lesson_blocks_module_id'), 'lesson_blocks', ['module_id'], unique=False)
    op.create_index(op.f('ix_lesson_blocks_org_id'), 'lesson_blocks', ['org_id'], unique=False)
    op.create_table('quiz_definitions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('org_id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('passing_score', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=50), nullable=True),
    sa.ForeignKeyConstraint(['deleted_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['module_id'], ['course_modules.id'], ),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_definitions_id'), 'quiz_definitions', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_definitions_module_id'), 'quiz_definitions', ['module_id'], unique=False)
    op.create_index(op.f('ix_quiz_definitions_org_id'), 'quiz_definitions', ['org_id'], unique=False)
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


def downgrade() -> None:
    op.drop_index(op.f('ix_quiz_questions_quiz_id'), table_name='quiz_questions')
    op.drop_index(op.f('ix_quiz_questions_org_id'), table_name='quiz_questions')
    op.drop_index(op.f('ix_quiz_questions_id'), table_name='quiz_questions')
    op.drop_table('quiz_questions')
    op.drop_index(op.f('ix_quiz_definitions_org_id'), table_name='quiz_definitions')
    op.drop_index(op.f('ix_quiz_definitions_module_id'), table_name='quiz_definitions')
    op.drop_index(op.f('ix_quiz_definitions_id'), table_name='quiz_definitions')
    op.drop_table('quiz_definitions')
    op.drop_index(op.f('ix_lesson_blocks_org_id'), table_name='lesson_blocks')
    op.drop_index(op.f('ix_lesson_blocks_module_id'), table_name='lesson_blocks')
    op.drop_index(op.f('ix_lesson_blocks_id'), table_name='lesson_blocks')
    op.drop_table('lesson_blocks')
    
    with op.batch_alter_table('course_modules', schema=None) as batch_op:
        batch_op.drop_constraint('fk_course_modules_deleted_by', type_='foreignkey')
        batch_op.drop_constraint('fk_course_modules_section_id', type_='foreignkey')
        batch_op.drop_column('deleted_by')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('status')
        batch_op.drop_column('section_id')
        
    op.drop_index(op.f('ix_learning_path_courses_id'), table_name='learning_path_courses')
    op.drop_table('learning_path_courses')
    op.drop_index(op.f('ix_media_assets_org_id'), table_name='media_assets')
    op.drop_index(op.f('ix_media_assets_id'), table_name='media_assets')
    op.drop_table('media_assets')
    op.drop_index(op.f('ix_learning_paths_status'), table_name='learning_paths')
    op.drop_index(op.f('ix_learning_paths_org_id'), table_name='learning_paths')
    op.drop_table('learning_paths')
    op.drop_index(op.f('ix_course_versions_status'), table_name='course_versions')
    op.drop_index(op.f('ix_course_versions_org_id'), table_name='course_versions')
    op.drop_index(op.f('ix_course_versions_course_id'), table_name='course_versions')
    op.drop_table('course_versions')
    op.drop_index(op.f('ix_course_sections_org_id'), table_name='course_sections')
    op.drop_index(op.f('ix_course_sections_id'), table_name='course_sections')
    op.drop_index(op.f('ix_course_sections_course_id'), table_name='course_sections')
    op.drop_table('course_sections')
