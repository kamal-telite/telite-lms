"""Course Module model."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.models.base import Base, TenantMixin, TimestampMixin


def _serialize_datetime(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class CourseModule(Base, TenantMixin, TimestampMixin):
    __tablename__ = "course_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    moodle_cmid: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="Moodle Course Module ID")
    
    section: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    section_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    module_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. page, url, quiz, scorm")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Optional URL or configuration data for the module
    content_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"), nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "course_id": self.course_id,
            "moodle_cmid": self.moodle_cmid,
            "section": self.section,
            "section_id": self.section_id,
            "status": self.status,
            "title": self.title,
            "module_type": self.module_type,
            "sort_order": self.sort_order,
            "content_url": self.content_url,
            "org_id": self.org_id,
            "created_at": _serialize_datetime(self.created_at),
            "deleted_at": _serialize_datetime(self.deleted_at),
            "deleted_by": self.deleted_by,
        }
