"""Enterprise Branding Engine models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BrandingVersion(Base, TimestampMixin):
    __tablename__ = "branding_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft, published, archived
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "version_number": self.version_number,
            "status": self.status,
            "configuration_json": self.configuration_json,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BrandingAsset(Base, TimestampMixin):
    __tablename__ = "branding_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "asset_type": self.asset_type,
            "file_path": self.file_path,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BrandingAuditLog(Base, TimestampMixin):
    __tablename__ = "branding_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    action: Mapped[str] = mapped_column(String(50), nullable=False) # draft_saved, published, rollback
    user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    changes_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]
        "Organization"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "action": self.action,
            "user_id": self.user_id,
            "changes_json": self.changes_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
