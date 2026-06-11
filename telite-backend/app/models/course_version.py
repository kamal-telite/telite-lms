from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from app.models.base import Base

class CourseVersion(Base):
    __tablename__ = "course_versions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(50), ForeignKey("courses.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    parent_version_id = Column(Integer, ForeignKey("course_versions.id"), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    published_by = Column(String(50), ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    snapshot_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "org_id": self.org_id,
            "version_number": self.version_number,
            "parent_version_id": self.parent_version_id,
            "status": self.status,
            "published_by": self.published_by,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "snapshot_summary": self._snapshot_summary(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def _snapshot_summary(self):
        snapshot = self.snapshot_json or {}
        sections = snapshot.get("sections") or []
        modules = [module for section in sections for module in section.get("modules", [])]
        blocks = [block for module in modules for block in module.get("blocks", [])]
        return {
            "sections": len(sections),
            "modules": len(modules),
            "blocks": len(blocks),
        }
