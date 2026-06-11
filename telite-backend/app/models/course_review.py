"""Course review workflow records."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


def _serialize_datetime(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class CourseReview(Base, TenantMixin):
    __tablename__ = "course_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "course_id": self.course_id,
            "org_id": self.org_id,
            "action": self.action,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "notes": self.notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": _serialize_datetime(self.reviewed_at),
        }
