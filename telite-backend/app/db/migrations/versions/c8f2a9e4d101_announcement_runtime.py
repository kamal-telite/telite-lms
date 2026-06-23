"""announcement runtime

Revision ID: c8f2a9e4d101
Revises: b7e2c4f91d33
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f2a9e4d101"
down_revision = "b7e2c4f91d33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="published"),
        sa.Column("created_by", sa.String(length=50), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcements_created_by", "announcements", ["created_by"])
    op.create_index("ix_announcements_org_id", "announcements", ["org_id"])
    op.create_index("ix_announcements_status", "announcements", ["status"])

    op.create_table(
        "announcement_audiences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("audience_type", sa.String(length=20), nullable=False),
        sa.Column("audience_value", sa.String(length=255), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcement_audiences_announcement_id", "announcement_audiences", ["announcement_id"])
    op.create_index("ix_announcement_audiences_audience_type", "announcement_audiences", ["audience_type"])
    op.create_index("ix_announcement_audiences_audience_value", "announcement_audiences", ["audience_value"])
    op.create_index("ix_announcement_audiences_org_id", "announcement_audiences", ["org_id"])

    op.create_table(
        "announcement_read_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("announcement_id", "user_id", "org_id", name="uq_announcement_read_state_user"),
    )
    op.create_index("ix_announcement_read_states_announcement_id", "announcement_read_states", ["announcement_id"])
    op.create_index("ix_announcement_read_states_org_id", "announcement_read_states", ["org_id"])
    op.create_index("ix_announcement_read_states_user_id", "announcement_read_states", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_announcement_read_states_user_id", table_name="announcement_read_states")
    op.drop_index("ix_announcement_read_states_org_id", table_name="announcement_read_states")
    op.drop_index("ix_announcement_read_states_announcement_id", table_name="announcement_read_states")
    op.drop_table("announcement_read_states")

    op.drop_index("ix_announcement_audiences_org_id", table_name="announcement_audiences")
    op.drop_index("ix_announcement_audiences_audience_value", table_name="announcement_audiences")
    op.drop_index("ix_announcement_audiences_audience_type", table_name="announcement_audiences")
    op.drop_index("ix_announcement_audiences_announcement_id", table_name="announcement_audiences")
    op.drop_table("announcement_audiences")

    op.drop_index("ix_announcements_status", table_name="announcements")
    op.drop_index("ix_announcements_org_id", table_name="announcements")
    op.drop_index("ix_announcements_created_by", table_name="announcements")
    op.drop_table("announcements")
