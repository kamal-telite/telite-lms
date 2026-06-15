"""Task assignment, submission, and review workflow models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class TaskAssignment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "learner_id", name="uq_task_assignments_task_learner"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(50), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    learner_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="assigned", index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("Task")
    learner = relationship("User", foreign_keys=[learner_id])


class TaskSubmission(Base, TenantMixin, TimestampMixin):
    __tablename__ = "task_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment = relationship("TaskAssignment")


class TaskReview(Base, TenantMixin, TimestampMixin):
    __tablename__ = "task_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submission = relationship("TaskSubmission")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
