"""
SQLAlchemy declarative base with shared mixins.

TenantMixin  — adds org_id FK to every tenant-scoped table
TimestampMixin — adds created_at / updated_at to every table
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base."""
    pass


class TimestampMixin:
    """Adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


class TenantMixin:
    """
    Adds org_id to every tenant-scoped table.

    This column is the anchor for PostgreSQL Row-Level Security policies.
    Every INSERT must supply org_id — the application layer enforces this.
    """

    org_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant organisation ID — used by RLS policies",
    )
