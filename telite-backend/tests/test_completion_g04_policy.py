from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.enrollment import EnrollmentRequest
from app.models.gradebook import CompletionRule, CourseGrade
from app.models.learner_event import LearnerEvent
from app.models.organization import Organization
from app.models.user import User
from app.services.completion_policy_service import CompletionPolicyError, CompletionPolicyService


ORG_ID = 7301


def _org(db: Session, org_id: int = ORG_ID) -> Organization:
    org = Organization(
        id=org_id,
        name=f"Completion Org {org_id}",
        type="company",
        domain=f"completion-{org_id}.example.edu",
        slug=f"completion-{org_id}",
        status="active",
        plan="pro",
    )
    db.add(org)
    db.flush()
    return org


def _user(db: Session, *, org_id: int = ORG_ID) -> User:
    user_id = f"learner-{uuid.uuid4().hex[:8]}"
    user = User(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
        full_name="Completion Learner",
        role="learner",
        category_scope="academics",
        org_id=org_id,
        organization_id=org_id,
        password_hash="not-used",
        avatar_initials="CL",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    db.add(user)
    db.flush()
    return user


def _course(db: Session, *, org_id: int = ORG_ID) -> tuple[Course, CourseModule]:
    course = Course(
        id=f"course-{uuid.uuid4().hex[:8]}",
        name="Completion Course",
        slug=f"completion-course-{uuid.uuid4().hex[:8]}",
        category_slug="academics",
        status="published",
        tier="Basic",
        org_id=org_id,
    )
    db.add(course)
    db.flush()
    module = CourseModule(
        course_id=course.id,
        title="Completion Module",
        module_type="page",
        status="published",
        org_id=org_id,
    )
    db.add(module)
    db.flush()
    return course, module


def _enroll(db: Session, user: User, course: Course, *, status: str = "in_progress", percentage: float = 0) -> CourseProgress:
    db.add(
        EnrollmentRequest(
            id=f"enrol-{uuid.uuid4().hex[:8]}",
            email=user.email,
            full_name=user.full_name,
            category_slug=course.category_slug,
            request_type="course",
            status="approved",
            org_id=user.org_id,
            requested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        )
    )
    progress = CourseProgress(
        user_id=user.id,
        course_id=course.id,
        org_id=user.org_id,
        status=status,
        completion_percentage=percentage,
        enrolled_version=1,
    )
    db.add(progress)
    db.flush()
    return progress


def _grade_rule(db: Session, course: Course, *, requires_instructor_approval: bool = False) -> CompletionRule:
    rule = CompletionRule(
        org_id=course.org_id,
        course_id=course.id,
        requires_content_completion=True,
        minimum_content_percentage=100,
        requires_grade_pass=True,
        minimum_final_percentage=60,
        requires_instructor_approval=requires_instructor_approval,
        certificate_eligible_on_completion=True,
        status="active",
        rule_json={},
    )
    db.add(rule)
    db.flush()
    return rule


def _course_grade(db: Session, user: User, course: Course, *, passed: bool, percentage: float) -> CourseGrade:
    grade = CourseGrade(
        org_id=course.org_id,
        course_id=course.id,
        course_version_id="1",
        user_id=user.id,
        percentage=percentage,
        display_grade=f"{percentage:.2f}%",
        passed=passed,
        status="calculated",
        metadata_json={},
    )
    db.add(grade)
    db.flush()
    return grade


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(payload={"sub": user.id, "org_id": user.org_id})
    return {"Authorization": f"Bearer {token}"}


def test_content_only_fallback_completes_existing_course(db_session: Session):
    _org(db_session)
    user = _user(db_session)
    course, _ = _course(db_session)
    progress = _enroll(db_session, user, course, percentage=100)

    result = CompletionPolicyService(db_session).evaluate_course_completion(
        user_id=user.id,
        course_id=course.id,
        org_id=ORG_ID,
        course_progress=progress,
    )

    assert result.completed is True
    assert result.completed_now is True
    assert result.new_state == "completed"
    assert progress.status == "completed"
    assert progress.completion_percentage == 100


def test_grade_aware_course_waits_for_passing_course_grade(db_session: Session):
    _org(db_session)
    user = _user(db_session)
    course, _ = _course(db_session)
    progress = _enroll(db_session, user, course, percentage=100)
    _grade_rule(db_session, course)

    result = CompletionPolicyService(db_session).evaluate_course_completion(
        user_id=user.id,
        course_id=course.id,
        org_id=ORG_ID,
        course_progress=progress,
    )

    assert result.completed is False
    assert result.completed_now is False
    assert result.new_state == "pending_grade"
    assert result.unmet_requirements == ["grade_passed"]
    assert progress.status == "pending_grade"
    assert progress.completion_percentage == 100


def test_grade_aware_course_completes_after_passing_course_grade(db_session: Session):
    _org(db_session)
    user = _user(db_session)
    course, _ = _course(db_session)
    progress = _enroll(db_session, user, course, status="pending_grade", percentage=100)
    _grade_rule(db_session, course)
    grade = _course_grade(db_session, user, course, passed=True, percentage=85)

    result = CompletionPolicyService(db_session).evaluate_course_completion(
        user_id=user.id,
        course_id=course.id,
        org_id=ORG_ID,
        course_progress=progress,
    )

    assert result.completed is True
    assert result.completed_now is True
    assert result.course_grade_id == grade.id
    assert result.new_state == "completed"
    assert progress.status == "completed"


def test_instructor_approval_rules_are_rejected_in_g04(db_session: Session):
    _org(db_session)
    user = _user(db_session)
    course, _ = _course(db_session)
    progress = _enroll(db_session, user, course, percentage=100)
    _grade_rule(db_session, course, requires_instructor_approval=True)

    try:
        CompletionPolicyService(db_session).evaluate_course_completion(
            user_id=user.id,
            course_id=course.id,
            org_id=ORG_ID,
            course_progress=progress,
        )
    except CompletionPolicyError as exc:
        assert "Instructor approval" in str(exc)
    else:
        raise AssertionError("Instructor approval rules must be rejected in G0.4")


def test_progress_endpoint_emits_course_completed_once_for_content_only_course(
    client: TestClient,
    db_session: Session,
):
    _org(db_session)
    user = _user(db_session)
    course, module = _course(db_session)
    _enroll(db_session, user, course)
    db_session.commit()

    payload = {
        "course_id": course.id,
        "module_updates": [{"module_id": module.id, "status": "completed"}],
    }
    first = client.post("/api/v1/learner/progress", json=payload, headers=_auth_headers(user))
    second = client.post("/api/v1/learner/progress", json=payload, headers=_auth_headers(user))

    assert first.status_code == 200
    assert first.json()["course_status"] == "completed"
    assert second.status_code == 200
    assert second.json()["course_status"] == "completed"
    assert (
        db_session.query(LearnerEvent)
        .filter_by(user_id=user.id, course_id=course.id, org_id=ORG_ID, event_type="COURSE_COMPLETED")
        .count()
        == 1
    )


def test_progress_endpoint_keeps_grade_aware_course_pending_until_passed(
    client: TestClient,
    db_session: Session,
):
    _org(db_session)
    user = _user(db_session)
    course, module = _course(db_session)
    _enroll(db_session, user, course)
    _grade_rule(db_session, course)
    db_session.commit()

    payload = {
        "course_id": course.id,
        "module_updates": [{"module_id": module.id, "status": "completed"}],
    }
    pending = client.post("/api/v1/learner/progress", json=payload, headers=_auth_headers(user))
    assert pending.status_code == 200
    assert pending.json()["course_status"] == "pending_grade"
    assert (
        db_session.query(LearnerEvent)
        .filter_by(user_id=user.id, course_id=course.id, org_id=ORG_ID, event_type="COURSE_COMPLETED")
        .count()
        == 0
    )

    _course_grade(db_session, user, course, passed=True, percentage=88)
    db_session.commit()

    completed = client.post("/api/v1/learner/progress", json=payload, headers=_auth_headers(user))
    assert completed.status_code == 200
    assert completed.json()["course_status"] == "completed"
    assert (
        db_session.query(LearnerEvent)
        .filter_by(user_id=user.id, course_id=course.id, org_id=ORG_ID, event_type="COURSE_COMPLETED")
        .count()
        == 1
    )
