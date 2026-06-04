"""Organization Branding model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class OrganizationBranding(Base, TimestampMixin):
    __tablename__ = "organization_branding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    login_banner_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    font_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    theme_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="light")
    
    certificate_template_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    landing_page_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization", back_populates="branding"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "logo_url": self.logo_url,
            "favicon_url": self.favicon_url,
            "login_banner_url": self.login_banner_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "font_family": self.font_family,
            "theme_mode": self.theme_mode,
            "certificate_template_url": self.certificate_template_url,
            "email_template_id": self.email_template_id,
            "landing_page_config": self.landing_page_config,
            "seo_title": self.seo_title,
            "seo_description": self.seo_description,
            "custom_domain": self.custom_domain,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
