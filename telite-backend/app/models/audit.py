"""Audit log and activity log models."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AuditLog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    accent: Mapped[str] = mapped_column(String(20), nullable=False, default="#2563EB")
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actor_user_id": self.actor_user_id,
            "actor_name": self.actor_name,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "message": self.message,
            "result": self.result,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ActivityLog(Base, TenantMixin, TimestampMixin):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    category_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    accent: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_slug": self.category_slug,
            "icon": self.icon,
            "accent": self.accent,
            "message": self.message,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
