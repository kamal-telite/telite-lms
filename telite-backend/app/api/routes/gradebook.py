"""Gradebook operations APIs for G0.6."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.models.gradebook import CourseGrade
from app.services.gradebook_access import require_learner_final_grade_visibility
from app.services.gradebook_operations_service import GradebookOperationsService
from app.services.gradebook_service import GradebookService


gradebook_router = APIRouter(tags=["Gradebook"])


class GradeOperationReason(BaseModel):
    reason: str | None = None


class GradeOverrideRequest(BaseModel):
    percentage: float = Field(ge=0, le=100)
    display_grade: str | None = None
    passed: bool | None = None
    points_awarded: float | None = None
    points_possible: float | None = None
    reason: str


def _actor_org_id(actor: TokenData, org_id: int | None) -> int:
    resolved = org_id if actor.is_platform_admin else actor.org_id
    if resolved is None:
        raise HTTPException(status_code=400, detail="Organization context is required")
    return resolved


@gradebook_router.get("/admin/gradebook/courses/{course_id}/course-grades")
def list_course_grades(
    course_id: str,
    org_id: int | None = Query(default=None),
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    grades = GradebookOperationsService(db).list_course_grades(
        actor=current_user,
        course_id=course_id,
        org_id=_actor_org_id(current_user, org_id),
    )
    return {"course_grades": [grade.to_dict() for grade in grades]}


@gradebook_router.post("/admin/gradebook/course-grades/{course_grade_id}/release")
def release_course_grade(
    course_grade_id: int,
    payload: GradeOperationReason,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    grade = GradebookOperationsService(db).release_course_grade(
        actor=current_user,
        course_grade_id=course_grade_id,
        reason=payload.reason,
    )
    db.commit()
    return {"course_grade": grade.to_dict()}


@gradebook_router.post("/admin/gradebook/course-grades/{course_grade_id}/lock")
def lock_course_grade(
    course_grade_id: int,
    payload: GradeOperationReason,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    grade = GradebookOperationsService(db).lock_course_grade(
        actor=current_user,
        course_grade_id=course_grade_id,
        reason=payload.reason,
    )
    db.commit()
    return {"course_grade": grade.to_dict()}


@gradebook_router.post("/admin/gradebook/course-grades/{course_grade_id}/override")
def override_course_grade(
    course_grade_id: int,
    payload: GradeOverrideRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    grade = GradebookOperationsService(db).override_course_grade(
        actor=current_user,
        course_grade_id=course_grade_id,
        percentage=payload.percentage,
        display_grade=payload.display_grade,
        passed=payload.passed,
        points_awarded=payload.points_awarded,
        points_possible=payload.points_possible,
        reason=payload.reason,
    )
    db.commit()
    return {"course_grade": grade.to_dict()}


@gradebook_router.get("/admin/gradebook/course-grades/{course_grade_id}/audit")
def list_course_grade_audit(
    course_grade_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    audit_rows = GradebookOperationsService(db).list_course_grade_audit(
        actor=current_user,
        course_grade_id=course_grade_id,
    )
    return {"audit": [row.to_dict() for row in audit_rows]}


@gradebook_router.get("/learner/gradebook/courses/{course_id}/final-grade")
def get_learner_final_grade(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    version_id = GradebookService(db).course_version_token(
        user_id=current_user.id,
        course_id=course_id,
        org_id=current_user.org_id,
    )
    grade = db.execute(
        select(CourseGrade).where(
            CourseGrade.org_id == current_user.org_id,
            CourseGrade.course_id == course_id,
            CourseGrade.user_id == current_user.id,
            CourseGrade.course_version_id == version_id,
        )
    ).scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Final grade not found")
    require_learner_final_grade_visibility(current_user, grade)
    return {"course_grade": grade.to_dict()}
