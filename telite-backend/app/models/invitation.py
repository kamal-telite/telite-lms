from __future__ import annotations

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class OrgInvitation(Base, TimestampMixin):
    __tablename__ = "org_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    invited_by: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    accepted_at: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_at: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sent_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_resent_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_attempted_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivered_at: Mapped[str | None] = mapped_column(String, nullable=True)
