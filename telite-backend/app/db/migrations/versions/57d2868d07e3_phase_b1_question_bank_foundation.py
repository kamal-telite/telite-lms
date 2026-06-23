"""phase_b1_question_bank_foundation

Revision ID: 57d2868d07e3
Revises: 43bc1c1ff92c
Create Date: 2026-06-21 17:04:46.194322

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57d2868d07e3'
down_revision: Union[str, None] = 'cp_enrolled_version_20260620'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _has_fk(table_name: str, columns: Sequence[str], referred_table: str) -> bool:
    if not _has_table(table_name):
        return False
    expected = tuple(columns)
    for fk in _inspector().get_foreign_keys(table_name):
        if tuple(fk.get("constrained_columns") or []) == expected and fk.get("referred_table") == referred_table:
            return True
    return False


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name not in _index_names(table_name):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.create_index(index_name, columns, unique=False)


def upgrade() -> None:
    if not _has_table('question_categories'):
        op.create_table('question_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['question_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    _create_index_if_missing('question_categories', op.f('ix_question_categories_id'), ['id'])
    _create_index_if_missing('question_categories', op.f('ix_question_categories_org_id'), ['org_id'])
    _create_index_if_missing('question_categories', op.f('ix_question_categories_parent_id'), ['parent_id'])

    if not _has_table('question_tags'):
        op.create_table('question_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    _create_index_if_missing('question_tags', op.f('ix_question_tags_id'), ['id'])
    _create_index_if_missing('question_tags', op.f('ix_question_tags_org_id'), ['org_id'])

    if not _has_table('question_import_jobs'):
        op.create_table('question_import_jobs',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    _create_index_if_missing('question_import_jobs', op.f('ix_question_import_jobs_id'), ['id'])
    _create_index_if_missing('question_import_jobs', op.f('ix_question_import_jobs_org_id'), ['org_id'])

    if not _has_table('question_tag_map'):
        op.create_table('question_tag_map',
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('question_version_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_version_id'], ['question_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['question_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('question_version_id', 'tag_id')
        )
    _create_index_if_missing('question_tag_map', op.f('ix_question_tag_map_org_id'), ['org_id'])

    question_version_columns = _column_names('question_versions')
    if 'status' not in question_version_columns:
        with op.batch_alter_table('question_versions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'))
        op.alter_column('question_versions', 'status', server_default=None)

    question_columns = _column_names('questions')
    with op.batch_alter_table('questions', schema=None) as batch_op:
        if 'category_id' not in question_columns:
            batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        if 'current_draft_version_id' not in question_columns:
            batch_op.add_column(sa.Column('current_draft_version_id', sa.Integer(), nullable=True))
        if 'current_published_version_id' not in question_columns:
            batch_op.add_column(sa.Column('current_published_version_id', sa.Integer(), nullable=True))
        if op.f('ix_questions_category_id') not in _index_names('questions'):
            batch_op.create_index(op.f('ix_questions_category_id'), ['category_id'], unique=False)
        op.execute("ALTER TABLE questions DROP CONSTRAINT IF EXISTS fk_question_current_version")
        if not _has_fk('questions', ['category_id'], 'question_categories'):
            batch_op.create_foreign_key('fk_questions_category_id', 'question_categories', ['category_id'], ['id'], ondelete='SET NULL')
        if not _has_fk('questions', ['current_published_version_id'], 'question_versions'):
            batch_op.create_foreign_key('fk_question_pub_version', 'question_versions', ['current_published_version_id'], ['id'], use_alter=True)
        if not _has_fk('questions', ['current_draft_version_id'], 'question_versions'):
            batch_op.create_foreign_key('fk_question_draft_version', 'question_versions', ['current_draft_version_id'], ['id'], use_alter=True)
        if 'current_version_id' in question_columns:
            batch_op.drop_column('current_version_id')


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_version_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.drop_constraint('fk_question_draft_version', type_='foreignkey')
        batch_op.drop_constraint('fk_question_pub_version', type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('fk_question_current_version', 'question_versions', ['current_version_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_questions_category_id'))
        batch_op.drop_column('current_published_version_id')
        batch_op.drop_column('current_draft_version_id')
        batch_op.drop_column('category_id')

    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.drop_column('status')

    with op.batch_alter_table('question_tag_map', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_question_tag_map_org_id'))

    op.drop_table('question_tag_map')
    with op.batch_alter_table('question_import_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_question_import_jobs_org_id'))
        batch_op.drop_index(batch_op.f('ix_question_import_jobs_id'))

    op.drop_table('question_import_jobs')
    with op.batch_alter_table('question_tags', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_question_tags_org_id'))
        batch_op.drop_index(batch_op.f('ix_question_tags_id'))

    op.drop_table('question_tags')
    with op.batch_alter_table('question_categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_question_categories_parent_id'))
        batch_op.drop_index(batch_op.f('ix_question_categories_org_id'))
        batch_op.drop_index(batch_op.f('ix_question_categories_id'))

    op.drop_table('question_categories')
    # ### end Alembic commands ###
