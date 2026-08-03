"""Notification preferences and defaults."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class NotificationCategory(str, enum.Enum):
    TASKS = "tasks"
    ASSIGNMENTS = "assignments"
    COURSES = "courses"
    ANNOUNCEMENTS = "announcements"
    MESSAGES = "messages"
    SECURITY = "security"
    SYSTEM = "system"
    MARKETING = "marketing"


class OrganizationNotificationDefault(Base, TimestampMixin):
    """Tenant-level default overrides for notification channels."""
    __tablename__ = "organization_notification_defaults"

    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    channel_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    channel_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NotificationPreference(Base, TenantMixin, TimestampMixin):
    """User-level overrides for notification channels."""
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    channel_email: Mapped[bool] = mapped_column(Boolean, nullable=False)
    channel_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False)
