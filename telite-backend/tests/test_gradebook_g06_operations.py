from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session as app_db_session
from app.main import create_app
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.gradebook import CourseGrade, GradeChangeAudit, GradeItem, GradeResult, GradingScheme
from app.models.organization import Organization
from app.models.user import User
from app.services.grade_aggregation_service import GradeAggregationService
from app.services.gradebook_operations_service import GradebookOperationsService
from app.services.gradebook_service import GradebookService


ORG_ID = 7601


def _token(
    user_id: str,
    *,
    role: str = "super_admin",
    org_id: int = ORG_ID,
    category_scope: str | None = "academics",
    is_platform_admin: bool = False,
) -> TokenData:
    return TokenData(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
        full_name=user_id.replace("-", " ").title(),
        role=role,
        org_id=org_id,
        category_scope=category_scope,
        is_platform_admin=is_platform_admin,
    )


def _seed_base(db: Session, *, category_slug: str = "academics") -> tuple[User, User, Course, CourseGrade]:
    org = Organization(
        id=ORG_ID,
        name="G06 Gradebook Org",
        type="college",
        domain="g06.example.edu",
        slug="g06-gradebook",
        status="active",
        plan="pro",
    )
    db.add(org)
    db.flush()
    admin = User(
        id="g06-admin",
        username="g06-admin",
        email="g06-admin@example.edu",
        full_name="G06 Admin",
        role="super_admin",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="GA",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    learner = User(
        id="g06-learner",
        username="g06-learner",
        email="g06-learner@example.edu",
        full_name="G06 Learner",
        role="learner",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="GL",
        gradient_start="#333333",
        gradient_end="#444444",
    )
    course = Course(
        id=f"g06-course-{uuid.uuid4().hex[:8]}",
        name="G06 Course",
        slug=f"g06-course-{uuid.uuid4().hex[:8]}",
        category_slug=category_slug,
        status="published",
        org_id=ORG_ID,
    )
    grade = CourseGrade(
        org_id=ORG_ID,
        course_id=course.id,
        course_version_id="1",
        user_id=learner.id,
        points_awarded=84,
        points_possible=100,
        percentage=84,
        display_grade="84.00%",
        passed=True,
        status="calculated",
        metadata_json={},
    )
    progress = CourseProgress(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=learner.id,
        status="completed",
        completion_percentage=100,
        enrolled_version=1,
    )
    db.add_all([admin, learner, course])
    db.flush()
    db.add_all([grade, progress])
    db.flush()
    return admin, learner, course, grade


def test_release_lock_and_override_write_append_only_audit(db_session: Session):
    admin, _, _, grade = _seed_base(db_session)
    actor = _token(admin.id)
    service = GradebookOperationsService(db_session)

    released = service.release_course_grade(actor=actor, course_grade_id=grade.id, reason="Final review complete")
    assert released.status == "released"

    locked = service.lock_course_grade(actor=actor, course_grade_id=grade.id, reason="Academic record finalized")
    assert locked.status == "locked"

    overridden = service.override_course_grade(
        actor=actor,
        course_grade_id=grade.id,
        percentage=91,
        passed=True,
        reason="Documented faculty appeal correction",
    )
    assert overridden.status == "overridden"
    assert overridden.percentage == 91
    assert overridden.override_by == admin.id

    rows = db_session.query(GradeChangeAudit).filter(GradeChangeAudit.course_grade_id == grade.id).order_by(GradeChangeAudit.id).all()
    assert [row.action for row in rows] == [
        "course_grade_released",
        "course_grade_locked",
        "course_grade_overridden",
    ]
    assert rows[-1].reason == "Documented faculty appeal correction"
    assert rows[-1].old_value_json["status"] == "locked"
    assert rows[-1].new_value_json["status"] == "overridden"


@pytest.mark.parametrize("reason", ["", "   ", "n/a", "test", "override", "short"])
def test_override_rejects_empty_whitespace_and_trivial_reasons(db_session: Session, reason: str):
    admin, _, _, grade = _seed_base(db_session)

    with pytest.raises(HTTPException) as exc:
        GradebookOperationsService(db_session).override_course_grade(
            actor=_token(admin.id),
            course_grade_id=grade.id,
            percentage=90,
            passed=True,
            reason=reason,
        )

    assert exc.value.status_code == 422


def test_platform_admin_cannot_mutate_learner_course_grades(db_session: Session):
    _, _, _, grade = _seed_base(db_session)

    with pytest.raises(HTTPException) as exc:
        GradebookOperationsService(db_session).release_course_grade(
            actor=_token("platform-admin", is_platform_admin=True, org_id=None, category_scope=None),
            course_grade_id=grade.id,
        )

    assert exc.value.status_code == 403
    assert "Platform admins cannot mutate" in exc.value.detail


def test_category_admin_scope_is_enforced(db_session: Session):
    admin, _, _, grade = _seed_base(db_session, category_slug="science")

    with pytest.raises(HTTPException) as exc:
        GradebookOperationsService(db_session).release_course_grade(
            actor=_token(admin.id, role="category_admin", category_scope="math"),
            course_grade_id=grade.id,
        )

    assert exc.value.status_code == 403


def test_learner_final_grade_api_only_returns_released_or_locked_grades(db_session: Session):
    _, learner, course, grade = _seed_base(db_session)
    app = create_app()

    def override_user():
        return _token(learner.id, role="learner")

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[app_db_session] = override_db_session
    client = TestClient(app)

    hidden = client.get(f"/api/v1/learner/gradebook/courses/{course.id}/final-grade")
    assert hidden.status_code == 404

    grade.status = "released"
    db_session.flush()
    visible = client.get(f"/api/v1/learner/gradebook/courses/{course.id}/final-grade")
    assert visible.status_code == 200
    assert visible.json()["course_grade"]["percentage"] == 84


def test_admin_release_api_writes_audit_row(db_session: Session):
    admin, _, _, grade = _seed_base(db_session)
    app = create_app()

    def override_user():
        return _token(admin.id)

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[app_db_session] = override_db_session
    client = TestClient(app)

    response = client.post(
        f"/api/v1/admin/gradebook/course-grades/{grade.id}/release",
        json={"reason": "Final review complete"},
    )

    assert response.status_code == 200
    assert response.json()["course_grade"]["status"] == "released"
    rows = db_session.query(GradeChangeAudit).filter(GradeChangeAudit.course_grade_id == grade.id).all()
    assert len(rows) == 1
    assert rows[0].action == "course_grade_released"


def test_overridden_course_grade_is_not_recalculated_by_new_grade_results(db_session: Session):
    admin, learner, course, grade = _seed_base(db_session)
    scheme = GradingScheme(
        org_id=ORG_ID,
        name="G06 Scheme",
        scheme_type="percentage",
        scale_json={},
        default_pass_threshold=60,
        rounding_mode="nearest",
        is_org_default=True,
        created_by=admin.id,
    )
    item = GradeItem(
        org_id=ORG_ID,
        course_id=course.id,
        source_type="quiz_block",
        source_id="quiz-1",
        title="Quiz",
        points_possible=100,
        is_required=True,
        is_extra_credit=False,
        grading_policy_json={"attempt_strategy": "latest"},
        created_by=admin.id,
    )
    db_session.add_all([scheme, item])
    db_session.flush()

    grade.status = "overridden"
    grade.percentage = 95
    grade.display_grade = "95.00%"
    grade.passed = True
    grade.override_by = admin.id
    grade.override_reason = "Documented faculty appeal correction"
    db_session.flush()

    GradebookService(db_session).upsert_current_result(
        org_id=ORG_ID,
        course_id=course.id,
        course_version_id="1",
        grade_item=item,
        user_id=learner.id,
        source_type="quiz_submission",
        source_id="attempt-2",
        attempt_number=2,
        points_awarded=10,
        points_possible=100,
        percentage=10,
        status="graded",
        graded_by=admin.id,
        graded_at=None,
        feedback=None,
        metadata={"attempt": 2},
    )

    recalculated = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=learner.id,
        course_version_id="1",
    )

    assert recalculated.id == grade.id
    assert recalculated.status == "overridden"
    assert recalculated.percentage == 95
    assert recalculated.display_grade == "95.00%"
