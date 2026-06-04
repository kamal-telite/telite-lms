"""Course model."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Course(Base, TenantMixin, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    moodle_course_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="Basic")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Content metadata
    module_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    modules_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    lessons_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Analytics
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_quiz_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Prerequisite
    prerequisite_course_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Pricing (for payment integration)
    price_paise: Mapped[int] = mapped_column(Integer, nullable=False, default=0,
                                              comment="Price in paise (INR × 100). 0 = free.")

    # Relationships
    category: Mapped["Category"] = relationship(  # type: ignore[name-defined]
        "Category",
        back_populates="courses",
        foreign_keys=[category_slug],
        primaryjoin="Course.category_slug == Category.slug",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "moodle_course_id": self.moodle_course_id,
            "category_slug": self.category_slug,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "tier": self.tier,
            "status": self.status,
            "module_count": self.module_count,
            "lessons_count": self.lessons_count,
            "hours": self.hours,
            "enrolled_count": self.enrolled_count,
            "completion_rate": self.completion_rate,
            "avg_quiz_score": self.avg_quiz_score,
            "price_paise": self.price_paise,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
