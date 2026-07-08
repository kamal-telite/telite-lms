"""Learning session ledger for active learner time tracking."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class LearningSession(Base, TenantMixin, TimestampMixin):
    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("course_modules.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lesson_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    end_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "module_id": self.module_id,
            "section_id": self.section_id,
            "block_id": self.block_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "active_seconds": self.active_seconds,
            "status": self.status,
            "end_reason": self.end_reason,
            "org_id": self.org_id,
        }
