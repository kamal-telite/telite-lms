from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base

class CourseSection(Base):
    __tablename__ = "course_sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(50), ForeignKey("courses.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "org_id": self.org_id,
            "title": self.title,
            "sort_order": self.sort_order,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }
