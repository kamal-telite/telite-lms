from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Text
from app.models.base import Base

class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    object_key = Column(String(255), nullable=False, unique=True)
    asset_version = Column(Integer, nullable=False, default=1)
    size_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(String(50), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "filename": self.filename,
            "object_key": self.object_key,
            "asset_version": self.asset_version,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }
