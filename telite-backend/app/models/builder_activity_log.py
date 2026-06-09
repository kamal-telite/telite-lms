"""Builder Activity Log model."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class BuilderActivityLog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "builder_activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "action": self.action,
            "payload": self.payload,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
