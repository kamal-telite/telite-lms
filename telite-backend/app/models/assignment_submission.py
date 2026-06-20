from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models.base import Base, TenantMixin

class AssignmentSubmission(Base, TenantMixin):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("lesson_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    submission_text = Column(Text, nullable=True)
    submission_files_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, server_default='[]')
    file_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(120), nullable=True)
    file_size = Column(Integer, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    
    status = Column(String(20), nullable=False, default="draft", index=True)
    grade = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    
    graded_by = Column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('block_id', 'user_id', name='uq_assignment_submission_block_user'),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'graded', 'returned', 'resubmitted')",
            name="chk_assignment_submissions_status",
        ),
    )

    @property
    def lesson_block_id(self):
        return self.block_id

    @property
    def learner_id(self):
        return self.user_id

    @property
    def organization_id(self):
        return self.org_id

    def to_dict(self):
        files = self.submission_files_json or []
        return {
            "id": self.id,
            "block_id": self.block_id,
            "lesson_block_id": self.block_id,
            "user_id": self.user_id,
            "learner_id": self.user_id,
            "org_id": self.org_id,
            "organization_id": self.org_id,
            "submission_text": self.submission_text,
            "submission_files_json": files,
            "files": files,
            "file_path": self.file_path,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "grade": self.grade,
            "feedback": self.feedback,
            "graded_by": self.graded_by,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
