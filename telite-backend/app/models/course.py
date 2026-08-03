"""Course model."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


def _serialize_datetime(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class Course(Base, TenantMixin, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("org_id", "slug", name="uq_courses_org_id_slug"),
        Index('ix_courses_org_category_status', 'org_id', 'category_slug', 'status'),
        CheckConstraint('module_count >= 0', name='chk_courses_module_count'),
        CheckConstraint('lessons_count >= 0', name='chk_courses_lessons_count'),
        CheckConstraint('hours >= 0', name='chk_courses_hours'),
        CheckConstraint('enrolled_count >= 0', name='chk_courses_enrolled_count'),
        CheckConstraint('completion_count >= 0', name='chk_courses_completion_count'),
        CheckConstraint('completion_rate >= 0 AND completion_rate <= 100', name='chk_courses_completion_rate'),
        CheckConstraint('avg_quiz_score >= 0 AND avg_quiz_score <= 100', name='chk_courses_avg_quiz_score'),
        CheckConstraint('price_paise >= 0', name='chk_courses_price_paise'),
        CheckConstraint("status IN ('draft', 'active', 'published', 'archived')", name='chk_courses_status'),
        CheckConstraint("tier IN ('Basic', 'Premium', 'Enterprise')", name='chk_courses_tier'),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="Basic")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    category: Mapped[Category] = relationship(  # type: ignore[name-defined]
        "Category",
        back_populates="courses",
        foreign_keys=[category_slug],
        primaryjoin="Course.category_slug == Category.slug",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category_slug": self.category_slug,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "tier": self.tier,
            "status": self.status,
            "cover_image_url": self.cover_image_url,
            "module_count": self.module_count,
            "lessons_count": self.lessons_count,
            "hours": self.hours,
            "enrolled_count": self.enrolled_count,
            "completion_rate": self.completion_rate,
            "completion_count": self.completion_count,
            "avg_quiz_score": self.avg_quiz_score,
            "price_paise": self.price_paise,
            "org_id": self.org_id,
            "created_at": _serialize_datetime(self.created_at),
        }
