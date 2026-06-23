"""Gradebook G0.6 course-grade operations."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.core.rbac import Permission
from app.models.gradebook import CourseGrade, GradeChangeAudit
from app.services.grade_audit_service import GradeAuditService
from app.services.gradebook_access import require_course_grade_mutation


TRIVIAL_REASONS = {"n/a", "na", "none", "test", "override", "manual", "because", "-"}


def validate_override_reason(reason: str | None) -> str:
    normalized = " ".join((reason or "").strip().split())
    if len(normalized) < 10 or normalized.lower() in TRIVIAL_REASONS:
        raise HTTPException(status_code=422, detail="Override reason must be specific and non-trivial.")
    return normalized


class GradebookOperationsService:
    def __init__(self, session: Session):
        self.session = session
        self.audit = GradeAuditService(session)

    def release_course_grade(self, *, actor: TokenData, course_grade_id: int, reason: str | None = None) -> CourseGrade:
        grade = self._get_course_grade(course_grade_id)
        require_course_grade_mutation(self.session, actor, grade, Permission.GRADEBOOK_RELEASE)
        if grade.status not in {"calculated", "overridden"}:
            raise HTTPException(status_code=409, detail=f"Course grade cannot be released from state '{grade.status}'.")

        old_value = grade.to_dict()
        grade.status = "released"
        grade.released_at = datetime.now(timezone.utc)
        self.session.flush()
        self.audit.record_course_grade_change(
            actor=actor,
            course_grade=grade,
            action="course_grade_released",
            old_value=old_value,
            new_value=grade.to_dict(),
            reason=reason,
        )
        return grade

    def lock_course_grade(self, *, actor: TokenData, course_grade_id: int, reason: str | None = None) -> CourseGrade:
        grade = self._get_course_grade(course_grade_id)
        require_course_grade_mutation(self.session, actor, grade, Permission.GRADEBOOK_LOCK)
        if grade.status not in {"calculated", "released", "overridden"}:
            raise HTTPException(status_code=409, detail=f"Course grade cannot be locked from state '{grade.status}'.")

        old_value = grade.to_dict()
        grade.status = "locked"
        grade.locked_at = datetime.now(timezone.utc)
        self.session.flush()
        self.audit.record_course_grade_change(
            actor=actor,
            course_grade=grade,
            action="course_grade_locked",
            old_value=old_value,
            new_value=grade.to_dict(),
            reason=reason,
        )
        return grade

    def override_course_grade(
        self,
        *,
        actor: TokenData,
        course_grade_id: int,
        percentage: float,
        reason: str,
        display_grade: str | None = None,
        passed: bool | None = None,
        points_awarded: float | None = None,
        points_possible: float | None = None,
    ) -> CourseGrade:
        normalized_reason = validate_override_reason(reason)
        if percentage < 0 or percentage > 100:
            raise HTTPException(status_code=422, detail="Override percentage must be between 0 and 100.")

        grade = self._get_course_grade(course_grade_id)
        require_course_grade_mutation(self.session, actor, grade, Permission.GRADEBOOK_OVERRIDE)

        old_value = grade.to_dict()
        grade.status = "overridden"
        grade.percentage = percentage
        grade.display_grade = display_grade or f"{percentage:.2f}%"
        grade.passed = passed
        if points_awarded is not None:
            grade.points_awarded = points_awarded
        if points_possible is not None:
            grade.points_possible = points_possible
        grade.override_by = actor.id
        grade.override_reason = normalized_reason
        grade.metadata_json = {
            **(grade.metadata_json or {}),
            "override_locked_from_auto_recalculation": True,
            "last_override_at": datetime.now(timezone.utc).isoformat(),
        }
        self.session.flush()
        self.audit.record_course_grade_change(
            actor=actor,
            course_grade=grade,
            action="course_grade_overridden",
            old_value=old_value,
            new_value=grade.to_dict(),
            reason=normalized_reason,
        )
        return grade

    def list_course_grades(self, *, actor: TokenData, course_id: str, org_id: int) -> list[CourseGrade]:
        from app.services.gradebook_access import get_scoped_course, require_course_scope, require_gradebook_capability

        require_gradebook_capability(self.session, actor, Permission.GRADEBOOK_VIEW)
        course = get_scoped_course(self.session, org_id=org_id, course_id=course_id)
        require_course_scope(self.session, actor, course)
        return list(
            self.session.execute(
                select(CourseGrade)
                .where(CourseGrade.org_id == org_id, CourseGrade.course_id == course_id)
                .order_by(CourseGrade.user_id, CourseGrade.course_version_id)
            ).scalars()
        )

    def list_course_grade_audit(self, *, actor: TokenData, course_grade_id: int) -> list[GradeChangeAudit]:
        from app.services.gradebook_access import require_gradebook_capability

        grade = self._get_course_grade(course_grade_id)
        require_gradebook_capability(self.session, actor, Permission.GRADEBOOK_AUDIT_VIEW)
        require_course_grade_mutation(self.session, actor, grade, Permission.GRADEBOOK_AUDIT_VIEW)
        return list(
            self.session.execute(
                select(GradeChangeAudit)
                .where(
                    GradeChangeAudit.org_id == grade.org_id,
                    GradeChangeAudit.course_grade_id == grade.id,
                )
                .order_by(GradeChangeAudit.created_at, GradeChangeAudit.id)
            ).scalars()
        )

    def _get_course_grade(self, course_grade_id: int) -> CourseGrade:
        grade = self.session.get(CourseGrade, course_grade_id)
        if not grade:
            raise HTTPException(status_code=404, detail="Course grade not found")
        return grade
