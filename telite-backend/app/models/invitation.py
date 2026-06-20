from __future__ import annotations

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class OrgInvitation(Base, TimestampMixin):
    __tablename__ = "org_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    category_scope: Mapped[str | None] = mapped_column(String, nullable=True)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    invited_by: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    accepted_at: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_at: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String, nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sent_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_resent_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_attempted_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivered_at: Mapped[str | None] = mapped_column(String, nullable=True)

    def is_expired(self) -> bool:
        from datetime import datetime
        if not self.expires_at:
            return False
        return datetime.utcnow().isoformat() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "email": self.email,
            "username": self.username,
            "role": self.role,
            "category_scope": self.category_scope,
            "token": self.token,
            "invited_by": self.invited_by,
            "expires_at": self.expires_at,
            "accepted_at": self.accepted_at,
            "revoked_at": self.revoked_at,
            "revoked_by": self.revoked_by,
            "revoke_reason": self.revoke_reason,
            "resend_count": self.resend_count,
            "last_sent_at": self.last_sent_at,
            "last_resent_at": self.last_resent_at,
            "delivery_status": self.delivery_status,
            "delivery_error": self.delivery_error,
            "delivery_attempted_at": self.delivery_attempted_at,
            "delivered_at": self.delivered_at,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
