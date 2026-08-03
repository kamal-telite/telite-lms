from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_key = Column(String(255), nullable=False)
    storage_provider = Column(String(50), nullable=False)
    url = Column(Text, nullable=False)
    folder = Column(String(120), nullable=True)
    tags_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    uploaded_by = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)

    # --- Compatibility properties ---
    # Many parts of the codebase reference the old attribute names.
    # These properties allow both old and new names to work.

    @property
    def filename(self):
        return self.file_name

    @property
    def mime_type(self):
        return self.file_type

    @property
    def size_bytes(self):
        return self.file_size

    @property
    def object_key(self):
        return self.storage_key

    @property
    def asset_version(self):
        return 1

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "filename": self.file_name,
            "file_name": self.file_name,
            "object_key": self.storage_key,
            "storage_key": self.storage_key,
            "asset_version": 1,
            "size_bytes": self.file_size,
            "file_size": self.file_size,
            "mime_type": self.file_type,
            "file_type": self.file_type,
            "url": self.url,
            "folder": self.folder,
            "tags": self.tags_json,
            "metadata_json": self.metadata_json,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }
