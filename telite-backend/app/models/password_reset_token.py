from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    org_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    token: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    used_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_attempted_at: Mapped[str | None] = mapped_column(String, nullable=True)
    delivered_at: Mapped[str | None] = mapped_column(String, nullable=True)
