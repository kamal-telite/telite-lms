"""Notification and activity log models."""

from __future__ import annotations

import enum
import json

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class NotificationType(str, enum.Enum):
    ENROLLMENT_CREATED = "enrollment_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_APPROVED = "task_approved"
    TASK_REJECTED = "task_rejected"
    TASK_REVISION_REQUESTED = "task_revision_requested"
    COURSE_PUBLISHED = "course_published"
    COURSE_REJECTED = "course_rejected"
    ASSIGNMENT_GRADED = "assignment_graded"
    CERTIFICATE_AWARDED = "certificate_awarded"
    LEARNING_PATH_ASSIGNED = "learning_path_assigned"
    LEARNING_PATH_UNLOCKED = "learning_path_unlocked"
    LEARNING_PATH_COMPLETED = "learning_path_completed"
    ANNOUNCEMENT_PUBLISHED = "announcement_published"
    INFO = "info"


class Notification(Base, TenantMixin, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index('ix_notifications_org_user_created', 'org_id', 'user_id', 'created_at'),
        Index('ix_notifications_org_user_read_created', 'org_id', 'user_id', 'is_read', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    def metadata_payload(self) -> dict:
        if not self.metadata_json:
            return {}
        if isinstance(self.metadata_json, dict):
            return self.metadata_json
        try:
            value = json.loads(self.metadata_json)
        except (TypeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "type": self.type,
            "is_read": self.is_read,
            "org_id": self.org_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata_json": self.metadata_payload(),
        }
