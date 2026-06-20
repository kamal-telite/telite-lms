"""add_user_theme_preference

Revision ID: theme_pref_20260619
Revises: onboarding_username_3
Create Date: 2026-06-19 19:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "theme_pref_20260619"
down_revision: Union[str, None] = "onboarding_username_3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("users")]

    if "theme_preference" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "theme_preference",
                sa.String(length=20),
                nullable=False,
                server_default="system",
            ),
        )

    constraints = [constraint["name"] for constraint in inspector.get_check_constraints("users")]
    if "chk_users_theme_preference" not in constraints:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.create_check_constraint(
                "chk_users_theme_preference",
                "theme_preference IN ('light', 'dark', 'system')",
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("users")]
    constraints = [constraint["name"] for constraint in inspector.get_check_constraints("users")]

    with op.batch_alter_table("users", schema=None) as batch_op:
        if "chk_users_theme_preference" in constraints:
            batch_op.drop_constraint("chk_users_theme_preference", type_="check")
        if "theme_preference" in columns:
            batch_op.drop_column("theme_preference")
