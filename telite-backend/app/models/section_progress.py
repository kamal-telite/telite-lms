"""Section Progress model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class SectionProgress(Base, TenantMixin, TimestampMixin):
    __tablename__ = "section_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    section_id: Mapped[int] = mapped_column(Integer, ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started", comment="not_started, in_progress, completed")
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total time spent in section in seconds")
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Last time learner entered the section")
    last_left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="Last time learner left the section")

    # Relationships
    user: Mapped[User] = relationship("User")
    section: Mapped[CourseSection] = relationship("CourseSection")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "section_id": self.section_id,
            "status": self.status,
            "completion_percentage": self.completion_percentage,
            "time_spent_seconds": self.time_spent_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_entered_at": self.last_entered_at.isoformat() if self.last_entered_at else None,
            "last_left_at": self.last_left_at.isoformat() if self.last_left_at else None,
            "org_id": self.org_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
