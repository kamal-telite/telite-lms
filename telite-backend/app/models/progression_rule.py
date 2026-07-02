"""Progression Rule model for module/section access control."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class ProgressionRule(Base, TenantMixin, TimestampMixin):
    """Rules controlling learner progression through modules and sections."""

    __tablename__ = "progression_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="module or section"
    )
    target_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="module_id or section_id"
    )
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="previous_module_completed, previous_section_completed, etc."
    )
    rule_value: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, comment="Rule-specific configuration"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "rule_type": self.rule_type,
            "rule_value": self.rule_value,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
