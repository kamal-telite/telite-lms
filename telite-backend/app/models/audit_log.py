"""Audit Log model for tracking granular entity changes."""

from __future__ import annotations

from sqlalchemy import Integer, String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    course_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "before_json": self.before_json,
            "after_json": self.after_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
