"""Append-only gradebook audit writer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.models.gradebook import CourseGrade, GradeChangeAudit


class GradeAuditService:
    def __init__(self, session: Session):
        self.session = session

    def record_course_grade_change(
        self,
        *,
        actor: TokenData,
        course_grade: CourseGrade,
        action: str,
        old_value: dict,
        new_value: dict,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> GradeChangeAudit:
        audit = GradeChangeAudit(
            org_id=course_grade.org_id,
            course_id=course_grade.course_id,
            course_version_id=course_grade.course_version_id,
            user_id=course_grade.user_id,
            course_grade_id=course_grade.id,
            actor_user_id=actor.id,
            actor_role=actor.role,
            action=action,
            old_value_json=old_value,
            new_value_json=new_value,
            reason=reason,
            metadata_json=metadata or {},
        )
        self.session.add(audit)
        self.session.flush()
        return audit
