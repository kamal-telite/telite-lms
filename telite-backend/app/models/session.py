"""Auth session model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class AuthSession(Base, TenantMixin, TimestampMixin):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[str] = mapped_column(String(20), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")  # type: ignore[name-defined]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "is_active": self.is_active,
            "org_id": self.org_id,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
