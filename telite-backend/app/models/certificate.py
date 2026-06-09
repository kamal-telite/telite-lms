"""Certificate model for tracking earned certificates."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Certificate(Base, TenantMixin, TimestampMixin):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="Public unique ID for verification")
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    pdf_s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    
    certificate_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    verification_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "pdf_s3_key": self.pdf_s3_key,
            "certificate_hash": self.certificate_hash,
            "verification_token": self.verification_token,
            "qr_code_url": self.qr_code_url,
            "issued_version": self.issued_version,
            "metadata": self.metadata_json,
            "org_id": self.org_id,
        }
