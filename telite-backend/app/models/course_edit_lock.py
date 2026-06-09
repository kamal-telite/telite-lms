"""Course Edit Lock model."""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class CourseEditLock(Base, TenantMixin):
    __tablename__ = "course_edit_locks"

    course_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    locked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "course_id": self.course_id,
            "user_id": self.user_id,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "org_id": self.org_id,
        }
