"""Course Progress model."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class CourseProgress(Base, TenantMixin, TimestampMixin):
    __tablename__ = "course_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started", comment="not_started, in_progress, completed")
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "status": self.status,
            "completion_percentage": self.completion_percentage,
            "time_spent_seconds": self.time_spent_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_viewed_at": self.last_viewed_at.isoformat() if self.last_viewed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "org_id": self.org_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
