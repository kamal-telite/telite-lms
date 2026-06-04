"""Task model."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Task(Base, TenantMixin, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_label: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_to_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    assignment_scope: Mapped[str] = mapped_column(String(50), nullable=False, default="individual")
    category_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    due_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    assigned_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_cross_category: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assigned_label": self.assigned_label,
            "assigned_to_user_id": self.assigned_to_user_id,
            "assignment_scope": self.assignment_scope,
            "category_slug": self.category_slug,
            "due_at": self.due_at,
            "status": self.status,
            "assigned_by": self.assigned_by,
            "notes": self.notes,
            "is_cross_category": self.is_cross_category,
            "org_id": self.org_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
