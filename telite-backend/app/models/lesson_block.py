from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.models.base import Base


class LessonBlock(Base):
    __tablename__ = "lesson_blocks"
    __table_args__ = (
        Index('ix_lesson_blocks_org_module_deleted_sort', 'org_id', 'module_id', 'deleted_at', 'sort_order'),
    )

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("course_modules.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    block_type = Column(String(50), nullable=False) # text, image, video, quiz_ref
    content = Column(Text, nullable=True)
    media_asset_id = Column(Integer, ForeignKey("media_assets.id"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, nullable=True) # AI, analytics, search, translation
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "module_id": self.module_id,
            "org_id": self.org_id,
            "block_type": self.block_type,
            "content": self.content,
            "media_asset_id": self.media_asset_id,
            "sort_order": self.sort_order,
            "metadata_json": self.metadata_json,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }
