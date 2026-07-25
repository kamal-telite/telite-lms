"""Announcement runtime models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Announcement(Base, TenantMixin, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published", index=True)
    created_by: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audiences: Mapped[list[AnnouncementAudience]] = relationship(
        "AnnouncementAudience",
        cascade="all, delete-orphan",
        back_populates="announcement",
    )

    def to_dict(self, *, is_read: bool | None = None, read_at: datetime | None = None) -> dict:
        payload = {
            "id": self.id,
            "org_id": self.org_id,
            "title": self.title,
            "body": self.body,
            "status": self.status,
            "created_by": self.created_by,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "audiences": [audience.to_dict() for audience in self.audiences],
        }
        if is_read is not None:
            payload["is_read"] = is_read
            payload["read_at"] = read_at.isoformat() if read_at else None
        return payload


class AnnouncementAudience(Base, TenantMixin, TimestampMixin):
    __tablename__ = "announcement_audiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    audience_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    audience_value: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    announcement: Mapped[Announcement] = relationship("Announcement", back_populates="audiences")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "announcement_id": self.announcement_id,
            "org_id": self.org_id,
            "audience_type": self.audience_type,
            "audience_value": self.audience_value,
        }


class AnnouncementReadState(Base, TenantMixin, TimestampMixin):
    __tablename__ = "announcement_read_states"
    __table_args__ = (
        UniqueConstraint(
            "announcement_id",
            "user_id",
            "org_id",
            name="uq_announcement_read_state_user",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
