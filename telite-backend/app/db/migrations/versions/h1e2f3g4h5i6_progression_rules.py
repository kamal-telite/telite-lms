"""progression rules for module/section locking

Revision ID: h1e2f3g4h5i6
Revises: g7c9d4e1f236
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "h1e2f3g4h5i6"
down_revision = "h8d2e5f9a642"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progression_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False, comment="module or section"),
        sa.Column("target_id", sa.Integer(), nullable=False, comment="module_id or section_id"),
        sa.Column("rule_type", sa.String(length=50), nullable=False, comment="previous_module_completed, previous_section_completed, etc."),
        sa.Column("rule_value", sa.JSON(), nullable=False, server_default=sa.text("'{}'"), comment="Rule-specific configuration"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.String(length=50), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["course_modules.id"], ondelete="CASCADE", name="fk_progression_rules_module"),
        sa.ForeignKeyConstraint(["target_id"], ["course_sections.id"], ondelete="CASCADE", name="fk_progression_rules_section"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_progression_rules_target", "progression_rules", ["target_type", "target_id"])
    op.create_index("ix_progression_rules_rule_type", "progression_rules", ["rule_type"])
    op.create_index("ix_progression_rules_org_id", "progression_rules", ["org_id"])
    op.create_index("ix_progression_rules_is_active", "progression_rules", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_progression_rules_is_active", table_name="progression_rules")
    op.drop_index("ix_progression_rules_org_id", table_name="progression_rules")
    op.drop_index("ix_progression_rules_rule_type", table_name="progression_rules")
    op.drop_index("ix_progression_rules_target", table_name="progression_rules")
    op.drop_table("progression_rules")
