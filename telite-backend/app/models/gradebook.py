"""Gradebook Core G0 models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class GradingScheme(Base, TenantMixin, TimestampMixin):
    """Organization-owned grading scheme for TELITE-native academic records."""

    __tablename__ = "grading_schemes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scheme_type: Mapped[str] = mapped_column(String(30), nullable=False, default="percentage", index=True)
    scale_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    default_pass_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=60.0)
    rounding_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="nearest")
    is_org_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "scheme_type": self.scheme_type,
            "scale_json": self.scale_json,
            "default_pass_threshold": self.default_pass_threshold,
            "rounding_mode": self.rounding_mode,
            "is_org_default": self.is_org_default,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GradeCategory(Base, TenantMixin, TimestampMixin):
    """Course-level grade category used for weighting grade items."""

    __tablename__ = "grade_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("course_versions.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    drop_lowest_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "name": self.name,
            "weight": self.weight,
            "drop_lowest_count": self.drop_lowest_count,
            "sort_order": self.sort_order,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GradeItem(Base, TenantMixin, TimestampMixin):
    """A TELITE-native graded item, usually generated from a quiz or assignment block."""

    __tablename__ = "grade_items"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "course_id",
            "source_type",
            "source_id",
            name="uq_grade_items_org_course_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("course_versions.id"), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("grade_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    points_possible: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_extra_credit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_released: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    grading_policy_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "attempt_strategy": "best",
            "missing_policy": "exclude_until_due",
            "late_policy": "none",
        },
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "category_id": self.category_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "points_possible": self.points_possible,
            "weight": self.weight,
            "is_required": self.is_required,
            "is_extra_credit": self.is_extra_credit,
            "is_released": self.is_released,
            "grading_policy_json": self.grading_policy_json,
            "sort_order": self.sort_order,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GradeResult(Base, TenantMixin, TimestampMixin):
    """Current learner gradebook result for a grade item and course version."""

    __tablename__ = "grade_results"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "course_version_id",
            "grade_item_id",
            "user_id",
            name="uq_grade_results_org_version_item_user",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version_id: Mapped[str] = mapped_column(String(50), nullable=False, default="current", index=True)
    grade_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("grade_items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points_awarded: Mapped[float | None] = mapped_column(Float, nullable=True)
    points_possible: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="graded", index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    graded_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "grade_item_id": self.grade_item_id,
            "user_id": self.user_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "attempt_number": self.attempt_number,
            "points_awarded": self.points_awarded,
            "points_possible": self.points_possible,
            "percentage": self.percentage,
            "status": self.status,
            "is_current": self.is_current,
            "graded_by": self.graded_by,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "feedback": self.feedback,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CourseGrade(Base, TenantMixin, TimestampMixin):
    """Materialized final course grade for a learner/course/version."""

    __tablename__ = "course_grades"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "course_id",
            "user_id",
            "course_version_id",
            name="uq_course_grades_org_course_user_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version_id: Mapped[str] = mapped_column(String(50), nullable=False, default="current", index=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    grading_scheme_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("grading_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    points_awarded: Mapped[float | None] = mapped_column(Float, nullable=True)
    points_possible: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    display_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "user_id": self.user_id,
            "grading_scheme_id": self.grading_scheme_id,
            "points_awarded": self.points_awarded,
            "points_possible": self.points_possible,
            "percentage": self.percentage,
            "display_grade": self.display_grade,
            "passed": self.passed,
            "status": self.status,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "override_by": self.override_by,
            "override_reason": self.override_reason,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GradeChangeAudit(Base, TenantMixin):
    """Append-only academic record audit trail for gradebook operations."""

    __tablename__ = "grade_change_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version_id: Mapped[str] = mapped_column(String(50), nullable=False, default="current", index=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_grade_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("course_grades.id", ondelete="SET NULL"), nullable=True, index=True)
    grade_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("grade_items.id", ondelete="SET NULL"), nullable=True, index=True)
    grade_result_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("grade_results.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    old_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    new_value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "user_id": self.user_id,
            "course_grade_id": self.course_grade_id,
            "grade_item_id": self.grade_item_id,
            "grade_result_id": self.grade_result_id,
            "actor_user_id": self.actor_user_id,
            "actor_role": self.actor_role,
            "action": self.action,
            "old_value_json": self.old_value_json,
            "new_value_json": self.new_value_json,
            "reason": self.reason,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CompletionRule(Base, TenantMixin, TimestampMixin):
    """Course or organization completion policy for G0.4."""

    __tablename__ = "completion_rules"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "course_id",
            "course_version_id",
            name="uq_completion_rules_org_course_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    course_version_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    grading_scheme_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("grading_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    requires_content_completion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    minimum_content_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    requires_grade_pass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    minimum_final_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_instructor_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certificate_eligible_on_completion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rule_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "org_id": self.org_id,
            "course_id": self.course_id,
            "course_version_id": self.course_version_id,
            "grading_scheme_id": self.grading_scheme_id,
            "status": self.status,
            "requires_content_completion": self.requires_content_completion,
            "minimum_content_percentage": self.minimum_content_percentage,
            "requires_grade_pass": self.requires_grade_pass,
            "minimum_final_percentage": self.minimum_final_percentage,
            "requires_instructor_approval": self.requires_instructor_approval,
            "certificate_eligible_on_completion": self.certificate_eligible_on_completion,
            "rule_json": self.rule_json,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
