"""Gradebook capability and scope helpers for academic-record operations."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.core.rbac import ROLE_PERMISSIONS, Permission
from app.models.course import Course
from app.models.gradebook import CourseGrade
from app.models.role_permission import RolePermission


GRADEBOOK_MUTATION_CAPABILITIES = {
    Permission.GRADEBOOK_RELEASE,
    Permission.GRADEBOOK_LOCK,
    Permission.GRADEBOOK_OVERRIDE,
}


def require_gradebook_capability(db: Session, actor: TokenData, capability: str) -> None:
    """Require a gradebook capability without allowing platform-grade mutation."""
    if actor.is_platform_admin and capability in GRADEBOOK_MUTATION_CAPABILITIES:
        raise HTTPException(
            status_code=403,
            detail="Platform admins cannot mutate learner academic records.",
        )

    if actor.is_platform_admin and capability in {Permission.GRADEBOOK_VIEW, Permission.GRADEBOOK_AUDIT_VIEW}:
        return

    if capability in (actor.permissions or []):
        return

    if capability in ROLE_PERMISSIONS.get(actor.role or "learner", set()):
        return

    if actor.org_id is not None:
        override = db.execute(
            select(RolePermission).where(
                RolePermission.org_id == actor.org_id,
                RolePermission.role == actor.role,
                RolePermission.permission_key == capability,
                RolePermission.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if override:
            return

    raise HTTPException(status_code=403, detail=f"You do not have the required capability: {capability}")


def get_scoped_course(db: Session, *, org_id: int, course_id: str) -> Course:
    course = db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.org_id == org_id,
        )
    ).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def require_course_scope(db: Session, actor: TokenData, course: Course) -> None:
    """Require actor org/category access to a course."""
    if actor.is_platform_admin:
        return
    if actor.org_id != course.org_id:
        raise HTTPException(status_code=403, detail="You do not have access to this organization")
    if actor.role == "category_admin":
        if not actor.category_scope:
            raise HTTPException(status_code=403, detail="Category admin has no category scope assigned.")
        if actor.category_scope != "all" and actor.category_scope != course.category_slug:
            raise HTTPException(status_code=403, detail="Course is outside your category scope.")


def require_course_grade_scope(db: Session, actor: TokenData, course_grade: CourseGrade) -> Course:
    course = get_scoped_course(db, org_id=course_grade.org_id, course_id=course_grade.course_id)
    require_course_scope(db, actor, course)
    return course


def require_course_grade_mutation(
    db: Session,
    actor: TokenData,
    course_grade: CourseGrade,
    capability: str,
) -> Course:
    require_gradebook_capability(db, actor, capability)
    return require_course_grade_scope(db, actor, course_grade)


def require_learner_final_grade_visibility(actor: TokenData, course_grade: CourseGrade) -> None:
    """Learners can see only their own official final course grades."""
    if actor.org_id != course_grade.org_id or actor.id != course_grade.user_id:
        raise HTTPException(status_code=404, detail="Final grade not found")
    if course_grade.status not in {"released", "locked"}:
        raise HTTPException(status_code=404, detail="Final grade not released")
