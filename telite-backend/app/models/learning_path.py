from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.models.base import Base

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    settings = Column(Text, nullable=False, default="{}") # Completion rules, prereqs
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "title": self.title,
            "description": self.description,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }

class LearningPathCourse(Base):
    __tablename__ = "learning_path_courses"
    
    path_id = Column(Integer, ForeignKey("learning_paths.id"), primary_key=True)
    course_id = Column(String(50), ForeignKey("courses.id"), primary_key=True)
    sort_order = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "path_id": self.path_id,
            "course_id": self.course_id,
            "sort_order": self.sort_order,
        }
