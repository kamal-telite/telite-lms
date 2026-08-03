from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from app.models.base import Base


class CourseSection(Base):
    __tablename__ = "course_sections"
    __table_args__ = (
        Index('ix_course_sections_org_course_deleted_sort', 'org_id', 'course_id', 'deleted_at', 'sort_order'),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(50), ForeignKey("courses.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    minimum_time_seconds = Column(Integer, nullable=False, default=0, comment="Minimum required learning time in seconds")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "org_id": self.org_id,
            "title": self.title,
            "sort_order": self.sort_order,
            "minimum_time_seconds": self.minimum_time_seconds,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by": self.deleted_by,
        }
