from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.gradebook import CompletionRule, CourseGrade
from app.models.organization import Organization
from app.models.user import User


def _learner() -> TokenData:
    return TokenData(
        id="learner-cert-1",
        username="learner-cert",
        email="learner-cert@example.com",
        full_name="Certificate Learner",
        role="learner",
        org_id=44,
    )


def _client(db_session) -> TestClient:
    app = create_app()

    def override_user():
        return _learner()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = override_db_session
    return TestClient(app)


def _seed_course(db_session) -> Course:
    org = Organization(
        id=44,
        name="Certificate Org",
        type="college",
        domain="cert.example.edu",
        slug="certificate-org",
        status="active",
        plan="free",
    )
    user = User(
        id="learner-cert-1",
        username="learner-cert",
        email="learner-cert@example.com",
        full_name="Certificate Learner",
        role="learner",
        org_id=44,
        organization_id=44,
        password_hash="not-used",
        avatar_initials="CL",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    course = Course(
        id="course-cert-1",
        org_id=44,
        category_slug="certificate-org",
        name="Certificate Runtime",
        slug="certificate-runtime",
        description="Certificate runtime verification",
        status="active",
    )
    db_session.add(org)
    db_session.commit()
    db_session.add_all([user, course])
    db_session.commit()
    return course


def test_certificate_issue_requires_completed_course_progress(db_session):
    _seed_course(db_session)
    client = _client(db_session)

    response = client.post("/api/certificates/course-cert-1/issue")

    assert response.status_code == 403
    assert response.json()["detail"] == "Course must be completed before issuing a certificate"


def test_certificate_issue_get_and_public_verify(db_session):
    _seed_course(db_session)
    progress = CourseProgress(
        org_id=44,
        user_id="learner-cert-1",
        course_id="course-cert-1",
        status="completed",
        completion_percentage=100,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(progress)
    db_session.commit()

    client = _client(db_session)

    issue_response = client.post("/api/certificates/course-cert-1/issue")
    assert issue_response.status_code == 200
    certificate = issue_response.json()["certificate"]
    assert certificate["user_id"] == "learner-cert-1"
    assert certificate["course_id"] == "course-cert-1"
    assert certificate["verification_token"]

    duplicate_response = client.post("/api/certificates/course-cert-1/issue")
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["certificate"]["id"] == certificate["id"]

    get_response = client.get("/api/certificates/course-cert-1")
    assert get_response.status_code == 200
    assert get_response.json()["certificate"]["id"] == certificate["id"]

    verify_response = client.get(f"/public/verify/{certificate['verification_token']}")
    assert verify_response.status_code == 200
    assert verify_response.json()["valid"] is True
    assert verify_response.json()["issued_to"] == "Certificate Learner"
    assert verify_response.json()["course_name"] == "Certificate Runtime"


def _grade_aware_rule(db_session, *, certificate_eligible: bool = True) -> CompletionRule:
    rule = CompletionRule(
        org_id=44,
        course_id="course-cert-1",
        requires_content_completion=True,
        minimum_content_percentage=100,
        requires_grade_pass=True,
        minimum_final_percentage=60,
        requires_instructor_approval=False,
        certificate_eligible_on_completion=certificate_eligible,
        status="active",
        rule_json={},
    )
    db_session.add(rule)
    db_session.flush()
    return rule


def _completed_progress(db_session, *, status: str = "completed") -> CourseProgress:
    progress = CourseProgress(
        org_id=44,
        user_id="learner-cert-1",
        course_id="course-cert-1",
        status=status,
        completion_percentage=100,
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        enrolled_version=1,
    )
    db_session.add(progress)
    db_session.flush()
    return progress


def _course_grade(db_session, *, passed: bool = True, percentage: float = 85) -> CourseGrade:
    grade = CourseGrade(
        org_id=44,
        course_id="course-cert-1",
        course_version_id="1",
        user_id="learner-cert-1",
        percentage=percentage,
        display_grade=f"{percentage:.2f}%",
        passed=passed,
        status="calculated",
        metadata_json={},
    )
    db_session.add(grade)
    db_session.flush()
    return grade


def test_certificate_issue_denies_pending_grade_course(db_session):
    _seed_course(db_session)
    _grade_aware_rule(db_session)
    _completed_progress(db_session, status="pending_grade")
    db_session.commit()
    client = _client(db_session)

    response = client.post("/api/certificates/course-cert-1/issue")

    assert response.status_code == 403
    assert response.json()["detail"] == "Course must be completed before issuing a certificate"


def test_certificate_issue_allows_grade_aware_completed_course(db_session):
    _seed_course(db_session)
    _grade_aware_rule(db_session)
    _completed_progress(db_session, status="completed")
    _course_grade(db_session, passed=True, percentage=88)
    db_session.commit()
    client = _client(db_session)

    response = client.post("/api/certificates/course-cert-1/issue")

    assert response.status_code == 200
    assert response.json()["certificate"]["course_id"] == "course-cert-1"


def test_certificate_issue_denies_when_completion_rule_disables_certificates(db_session):
    _seed_course(db_session)
    _grade_aware_rule(db_session, certificate_eligible=False)
    _completed_progress(db_session, status="completed")
    _course_grade(db_session, passed=True, percentage=88)
    db_session.commit()
    client = _client(db_session)

    response = client.post("/api/certificates/course-cert-1/issue")

    assert response.status_code == 403
    assert response.json()["detail"] == "Course must be completed before issuing a certificate"
