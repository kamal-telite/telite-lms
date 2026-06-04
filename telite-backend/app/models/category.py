"""Category (department/school) model."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Category(Base, TenantMixin, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    accent_color: Mapped[str] = mapped_column(String(20), nullable=False, default="#2563EB")
    admin_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    planned_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_pal_target: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    moodle_category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    org_type: Mapped[str] = mapped_column(String(50), nullable=False, default="college")
    archived_at: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Legacy column — kept for backward compat; org_id (TenantMixin) is canonical
    organization_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization", back_populates="categories", foreign_keys=[organization_id]
    )
    courses: Mapped[list["Course"]] = relationship(  # type: ignore[name-defined]
        "Course", back_populates="category", foreign_keys="Course.category_slug",
        primaryjoin="Category.slug == Course.category_slug",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "status": self.status,
            "accent_color": self.accent_color,
            "admin_user_id": self.admin_user_id,
            "planned_courses": self.planned_courses,
            "avg_pal_target": self.avg_pal_target,
            "org_id": self.org_id,
            "organization_id": self.organization_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
