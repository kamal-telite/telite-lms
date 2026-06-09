"""Lesson Block Progress model."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class LessonBlockProgress(Base, TenantMixin, TimestampMixin):
    __tablename__ = "lesson_block_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[int] = mapped_column(Integer, ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, ForeignKey("lesson_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started", comment="not_started, completed")
    video_position_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Resume position for video blocks")
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    module: Mapped["CourseModule"] = relationship("CourseModule")
    block: Mapped["LessonBlock"] = relationship("LessonBlock")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "module_id": self.module_id,
            "block_id": self.block_id,
            "status": self.status,
            "video_position_seconds": self.video_position_seconds,
            "completion_percentage": self.completion_percentage,
            "time_spent_seconds": self.time_spent_seconds,
            "last_viewed_at": self.last_viewed_at.isoformat() if self.last_viewed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "org_id": self.org_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
