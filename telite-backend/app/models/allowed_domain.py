from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class AllowedDomain(Base, TimestampMixin):
    __tablename__ = "allowed_domains"

    domain: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    added_by: Mapped[str | None] = mapped_column(String, nullable=True)
    org_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
