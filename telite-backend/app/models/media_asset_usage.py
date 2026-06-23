from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base, TenantMixin, TimestampMixin

class MediaAssetUsage(Base, TenantMixin, TimestampMixin):
    __tablename__ = "media_asset_usages"

    id = Column(Integer, primary_key=True, index=True)
    media_asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    entity_type = Column(String(50), nullable=False, index=True) # e.g., 'lesson_block', 'question', 'assignment'
    entity_id = Column(String(50), nullable=False, index=True)   # ID of the referring entity
    usage_context = Column(String(50), nullable=False)           # e.g., 'primary_asset', 'metadata_reference'

    def to_dict(self):
        return {
            "id": self.id,
            "media_asset_id": self.media_asset_id,
            "org_id": self.org_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "usage_context": self.usage_context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
