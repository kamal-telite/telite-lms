from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.models.base import Base, TenantMixin
from app.core.assignment_statuses import can_resubmit, normalize_status, status_label


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
    course_time_seconds_at_submission = Column(Integer, nullable=False, default=0)
    course_progress_pct_at_submission = Column(Float, nullable=False, default=0.0)
    
    graded_by = Column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint('block_id', 'user_id', name='uq_assignment_submission_block_user'),
        Index('ix_assignment_submissions_org_block_user', 'org_id', 'block_id', 'user_id'),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'graded', 'returned', 'resubmitted', 'pending_verification', 'approved', 'rejected')",
            name="chk_assignment_submissions_status",
        ),
        CheckConstraint('attempt_number >= 1', name='chk_assignment_submissions_attempt_number'),
        CheckConstraint('course_progress_pct_at_submission >= 0 AND course_progress_pct_at_submission <= 100', name='chk_assignment_submissions_course_progress_pct'),
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
        normalized_status = normalize_status(self.status)
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
            "normalized_status": normalized_status,
            "status_display": normalized_status,
            "status_label": status_label(self.status),
            "can_resubmit": can_resubmit(self.status),
            "grade": self.grade,
            "feedback": self.feedback,
            "course_time_seconds_at_submission": self.course_time_seconds_at_submission or 0,
            "course_progress_pct_at_submission": self.course_progress_pct_at_submission or 0.0,
            "graded_by": self.graded_by,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
