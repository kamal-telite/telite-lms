"""Interactive tracking model for SCORM/xAPI state."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class InteractiveTracking(Base, TenantMixin, TimestampMixin):
    __tablename__ = "interactive_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("module_progress.id", ondelete="CASCADE"), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False, comment="scorm_12, scorm_2004, xapi")
    element: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="e.g. cmi.suspend_data")
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    attempt: Mapped["ModuleProgress"] = relationship("ModuleProgress")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "attempt_id": self.attempt_id,
            "protocol": self.protocol,
            "element": self.element,
            "value": self.value,
            "org_id": self.org_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
