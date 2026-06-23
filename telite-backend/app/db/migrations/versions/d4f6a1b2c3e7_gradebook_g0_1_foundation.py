"""gradebook g0.1 foundation

Revision ID: d4f6a1b2c3e7
Revises: c8f2a9e4d101
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "d4f6a1b2c3e7"
down_revision = "c8f2a9e4d101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grading_schemes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scheme_type", sa.String(length=30), nullable=False, server_default="percentage"),
        sa.Column("scale_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("default_pass_threshold", sa.Float(), nullable=False, server_default="60"),
        sa.Column("rounding_mode", sa.String(length=30), nullable=False, server_default="nearest"),
        sa.Column("is_org_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grading_schemes_created_by", "grading_schemes", ["created_by"])
    op.create_index("ix_grading_schemes_is_org_default", "grading_schemes", ["is_org_default"])
    op.create_index("ix_grading_schemes_org_id", "grading_schemes", ["org_id"])
    op.create_index("ix_grading_schemes_scheme_type", "grading_schemes", ["scheme_type"])

    op.create_table(
        "grade_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("course_version_id", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("drop_lowest_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_version_id"], ["course_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_grade_categories_course_id", "grade_categories", ["course_id"])
    op.create_index("ix_grade_categories_course_version_id", "grade_categories", ["course_version_id"])
    op.create_index("ix_grade_categories_created_by", "grade_categories", ["created_by"])
    op.create_index("ix_grade_categories_org_id", "grade_categories", ["org_id"])

    op.create_table(
        "grade_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.String(length=50), nullable=False),
        sa.Column("course_version_id", sa.String(length=50), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("points_possible", sa.Float(), nullable=False, server_default="100"),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_extra_credit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "grading_policy_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{\"attempt_strategy\":\"best\",\"missing_policy\":\"exclude_until_due\",\"late_policy\":\"none\"}'"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["grade_categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_version_id"], ["course_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "course_id", "source_type", "source_id", name="uq_grade_items_org_course_source"),
    )
    op.create_index("ix_grade_items_category_id", "grade_items", ["category_id"])
    op.create_index("ix_grade_items_course_id", "grade_items", ["course_id"])
    op.create_index("ix_grade_items_course_version_id", "grade_items", ["course_version_id"])
    op.create_index("ix_grade_items_created_by", "grade_items", ["created_by"])
    op.create_index("ix_grade_items_is_released", "grade_items", ["is_released"])
    op.create_index("ix_grade_items_org_id", "grade_items", ["org_id"])
    op.create_index("ix_grade_items_source_id", "grade_items", ["source_id"])
    op.create_index("ix_grade_items_source_type", "grade_items", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_grade_items_source_type", table_name="grade_items")
    op.drop_index("ix_grade_items_source_id", table_name="grade_items")
    op.drop_index("ix_grade_items_org_id", table_name="grade_items")
    op.drop_index("ix_grade_items_is_released", table_name="grade_items")
    op.drop_index("ix_grade_items_created_by", table_name="grade_items")
    op.drop_index("ix_grade_items_course_version_id", table_name="grade_items")
    op.drop_index("ix_grade_items_course_id", table_name="grade_items")
    op.drop_index("ix_grade_items_category_id", table_name="grade_items")
    op.drop_table("grade_items")

    op.drop_index("ix_grade_categories_org_id", table_name="grade_categories")
    op.drop_index("ix_grade_categories_created_by", table_name="grade_categories")
    op.drop_index("ix_grade_categories_course_version_id", table_name="grade_categories")
    op.drop_index("ix_grade_categories_course_id", table_name="grade_categories")
    op.drop_table("grade_categories")

    op.drop_index("ix_grading_schemes_scheme_type", table_name="grading_schemes")
    op.drop_index("ix_grading_schemes_org_id", table_name="grading_schemes")
    op.drop_index("ix_grading_schemes_is_org_default", table_name="grading_schemes")
    op.drop_index("ix_grading_schemes_created_by", table_name="grading_schemes")
    op.drop_table("grading_schemes")
