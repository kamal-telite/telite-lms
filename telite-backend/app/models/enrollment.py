"""Enrollment request model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class EnrollmentRequest(Base, TenantMixin, TimestampMixin):
    __tablename__ = "enrollment_requests"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    requested_at: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "category_slug": self.category_slug,
            "request_type": self.request_type,
            "status": self.status,
            "requested_at": self.requested_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "rejection_reason": self.rejection_reason,
            "org_id": self.org_id,
        }
