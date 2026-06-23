from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.user import User


def _learner(user_id: str = "learner-cert-1", org_id: int = 44) -> TokenData:
    return TokenData(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
        full_name=f"{user_id} Name",
        role="learner",
        org_id=org_id,
    )


def _client(db_session, user: TokenData | None = None) -> TestClient:
    app = create_app()

    def override_user():
        return user or _learner()

    def override_db_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = override_db_session
    return TestClient(app)


def _seed_course(db_session) -> None:
    org = Organization(
        id=44,
        name="Certificate Notification Org",
        type="college",
        domain="cert-notification.example.edu",
        slug="certificate-notification-org",
        status="active",
        plan="free",
    )
    other_org = Organization(
        id=45,
        name="Other Certificate Org",
        type="college",
        domain="other-cert.example.edu",
        slug="other-certificate-org",
        status="active",
        plan="free",
    )
    db_session.add_all([org, other_org])
    db_session.commit()

    users = [
        User(
            id="learner-cert-1",
            username="learner-cert-1",
            email="learner-cert-1@example.com",
            full_name="Certificate Learner",
            role="learner",
            org_id=44,
            organization_id=44,
            password_hash="not-used",
            avatar_initials="CL",
            gradient_start="#111111",
            gradient_end="#222222",
        ),
        User(
            id="learner-cert-2",
            username="learner-cert-2",
            email="learner-cert-2@example.com",
            full_name="Same Org Learner",
            role="learner",
            org_id=44,
            organization_id=44,
            password_hash="not-used",
            avatar_initials="SL",
            gradient_start="#111111",
            gradient_end="#222222",
        ),
        User(
            id="learner-cert-other",
            username="learner-cert-other",
            email="learner-cert-other@example.com",
            full_name="Other Org Learner",
            role="learner",
            org_id=45,
            organization_id=45,
            password_hash="not-used",
            avatar_initials="OL",
            gradient_start="#111111",
            gradient_end="#222222",
        ),
    ]
    course = Course(
        id="course-cert-1",
        org_id=44,
        category_slug="certificate-notification-org",
        name="Certificate Notification Runtime",
        slug="certificate-notification-runtime",
        description="Certificate notification verification",
        status="active",
    )
    progress = CourseProgress(
        org_id=44,
        user_id="learner-cert-1",
        course_id="course-cert-1",
        status="completed",
        completion_percentage=100,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([*users, course, progress])
    db_session.commit()


def test_certificate_awarded_notification_created_once_and_contract_valid(db_session):
    _seed_course(db_session)
    client = _client(db_session)

    issue_response = client.post("/api/certificates/course-cert-1/issue")
    assert issue_response.status_code == 200
    certificate = issue_response.json()["certificate"]

    notifications = db_session.query(Notification).filter(
        Notification.user_id == "learner-cert-1",
        Notification.type == "certificate_awarded",
    ).all()
    assert len(notifications) == 1
    notification = notifications[0]
    metadata = notification.metadata_payload()

    assert notification.org_id == 44
    assert notification.source_type == "certificate"
    assert notification.source_id == certificate["id"]
    assert metadata["route"] == "/learner/certificates"
    assert metadata["route_name"] == "learner_certificates"
    assert metadata["course_id"] == "course-cert-1"
    assert metadata["certificate_id"] == certificate["id"]
    assert metadata["verification_token"] == certificate["verification_token"]
    assert metadata["idempotency_key"] == f"learner-cert-1:certificate_awarded:{certificate['id']}"

    duplicate_response = client.post("/api/certificates/course-cert-1/issue")
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["certificate"]["id"] == certificate["id"]

    duplicate_count = db_session.query(Notification).filter(
        Notification.user_id == "learner-cert-1",
        Notification.type == "certificate_awarded",
    ).count()
    assert duplicate_count == 1


def test_certificate_awarded_unread_mark_read_and_tenant_isolation(db_session):
    _seed_course(db_session)
    client = _client(db_session)
    issue_response = client.post("/api/certificates/course-cert-1/issue")
    assert issue_response.status_code == 200
    certificate = issue_response.json()["certificate"]

    unread = client.get("/api/v1/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["count"] == 1

    listing = client.get("/api/v1/notifications")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "certificate_awarded"
    assert items[0]["metadata_json"]["route"] == "/learner/certificates"

    mark_read = client.patch(f"/api/v1/notifications/{items[0]['id']}/read")
    assert mark_read.status_code == 200

    unread_after = client.get("/api/v1/notifications/unread-count")
    assert unread_after.status_code == 200
    assert unread_after.json()["count"] == 0

    same_org_other = _client(db_session, _learner("learner-cert-2", 44))
    assert same_org_other.get("/api/v1/notifications").json()["items"] == []

    cross_org_other = _client(db_session, _learner("learner-cert-other", 45))
    assert cross_org_other.get("/api/v1/notifications").json()["items"] == []

    assert db_session.query(Notification).filter(
        Notification.source_type == "certificate",
        Notification.source_id == certificate["id"],
        Notification.user_id != "learner-cert-1",
    ).count() == 0
