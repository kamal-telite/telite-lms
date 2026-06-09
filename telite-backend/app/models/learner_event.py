"""Learner Event model."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, TenantMixin


class LearnerEvent(Base, TenantMixin):
    __tablename__ = "learner_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    module_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("course_modules.id", ondelete="CASCADE"), nullable=True, index=True)
    block_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lesson_blocks.id", ondelete="CASCADE"), nullable=True, index=True)
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(10), nullable=False, default="v1")
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "module_id": self.module_id,
            "block_id": self.block_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "payload_json": self.payload_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
