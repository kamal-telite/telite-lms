"""Organization (tenant) model — root of the multi-tenant hierarchy."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)          # college / company
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")

    # Moodle integration
    moodle_category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    moodle_tenant_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Admin linkage
    admin_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Branding (Phase 7 isolated table) ───────────────────────
    branding: Mapped["OrganizationBranding"] = relationship(  # type: ignore[name-defined]
        "OrganizationBranding", back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User", back_populates="organization", foreign_keys="User.org_id"
    )
    memberships: Mapped[list["Membership"]] = relationship(  # type: ignore[name-defined]
        "Membership", back_populates="organization"
    )
    categories: Mapped[list["Category"]] = relationship(  # type: ignore[name-defined]
        "Category", back_populates="organization", foreign_keys="Category.organization_id"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "domain": self.domain,
            "slug": self.slug,
            "status": self.status,
            "plan": self.plan,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "branding": self.branding.to_dict() if self.branding else None,
        }
