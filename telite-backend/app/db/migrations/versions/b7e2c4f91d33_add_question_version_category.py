"""add question version category

Revision ID: b7e2c4f91d33
Revises: 9b2c7f4d1a6e
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa


revision = "b7e2c4f91d33"
down_revision = "9b2c7f4d1a6e"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("question_versions", "category_id"):
        op.add_column("question_versions", sa.Column("category_id", sa.Integer(), nullable=True))
        op.create_index("ix_question_versions_category_id", "question_versions", ["category_id"])
        op.create_foreign_key(
            "fk_question_versions_category_id",
            "question_versions",
            "question_categories",
            ["category_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        """
        UPDATE question_versions qv
        SET category_id = q.category_id
        FROM questions q
        WHERE qv.question_id = q.id
          AND qv.category_id IS NULL
        """
    )


def downgrade() -> None:
    if _has_column("question_versions", "category_id"):
        op.drop_constraint("fk_question_versions_category_id", "question_versions", type_="foreignkey")
        op.drop_index("ix_question_versions_category_id", table_name="question_versions")
        op.drop_column("question_versions", "category_id")
