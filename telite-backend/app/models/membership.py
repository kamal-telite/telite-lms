"""
Membership model — maps users to organisations with roles.

PHASE 3 NEW TABLE: Enables one user to belong to multiple organisations
with different roles in each (e.g., super_admin in Org A, learner in Org B).
This is the correct enterprise multi-tenant RBAC pattern.

Replaces the flat role/org_id columns on the users table for role resolution.
The users table columns are kept for backward compatibility during migration.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role within this specific organisation
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional category scope for category_admin role
    category_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status: active / suspended / invited
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Who granted this membership
    granted_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")  # type: ignore[name-defined]
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization", back_populates="memberships"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "category_scope": self.category_scope,
            "status": self.status,
            "granted_by": self.granted_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
