"""User model."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_initials: Mapped[str] = mapped_column(String(5), nullable=False)
    gradient_start: Mapped[str] = mapped_column(String(20), nullable=False)
    gradient_end: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # PAL metrics
    pal_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pal_completion_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pal_quiz_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pal_time_spent_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pal_task_completion_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Progress
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    courses_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_courses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cohort_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_course_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    course_progress_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    # Profile
    program: Mapped[str | None] = mapped_column(String(100), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    moodle_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_login: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invited_via: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Legacy column — kept for backward compat, org_id is canonical
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization", back_populates="users", foreign_keys="User.org_id"
    )
    memberships: Mapped[list["Membership"]] = relationship(  # type: ignore[name-defined]
        "Membership", back_populates="user"
    )
    sessions: Mapped[list["AuthSession"]] = relationship(  # type: ignore[name-defined]
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self, include_hash: bool = False) -> dict:
        d = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "category_scope": self.category_scope,
            "avatar_initials": self.avatar_initials,
            "gradient_start": self.gradient_start,
            "gradient_end": self.gradient_end,
            "is_active": self.is_active,
            "is_platform_admin": self.is_platform_admin,
            "status": self.status,
            "org_id": self.org_id,
            "pal_score": self.pal_score,
            "streak_days": self.streak_days,
            "courses_completed": self.courses_completed,
            "moodle_id": self.moodle_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login,
        }
        if include_hash:
            d["password_hash"] = self.password_hash
        return d
