from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.learner_event import LearnerEvent
from app.models.learning_path import LearningPath, LearningPathCourse
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.user import User
from app.repositories.learning_path_progress_repo import LearningPathProgressRepository
from app.services.learning_path_unlock_service import LearningPathUnlockService


ORG_ID = 71
OTHER_ORG_ID = 72
LEARNER_ID = "learner-lpn-1"
SAME_ORG_OTHER_ID = "learner-lpn-2"
CROSS_ORG_ID = "learner-lpn-cross"
PATH_ID = 7101


def _learner(user_id: str = LEARNER_ID, org_id: int = ORG_ID) -> TokenData:
    return TokenData(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
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


def _seed_path(db_session) -> LearningPath:
    org = Organization(
        id=ORG_ID,
        name="Learning Path Notification Org",
        type="company",
        domain="learning-path-notification.example.edu",
        slug="learning-path-notification-org",
        status="active",
        plan="free",
    )
    other_org = Organization(
        id=OTHER_ORG_ID,
        name="Other Learning Path Notification Org",
        type="company",
        domain="other-learning-path-notification.example.edu",
        slug="other-learning-path-notification-org",
        status="active",
        plan="free",
    )
    users = [
        User(
            id=LEARNER_ID,
            username=LEARNER_ID,
            email="learner-lpn-1@example.edu",
            full_name="Learning Path Notification Learner",
            role="learner",
            org_id=ORG_ID,
            organization_id=ORG_ID,
            password_hash="not-used",
            avatar_initials="LN",
            gradient_start="#111111",
            gradient_end="#222222",
        ),
        User(
            id=SAME_ORG_OTHER_ID,
            username=SAME_ORG_OTHER_ID,
            email="learner-lpn-2@example.edu",
            full_name="Same Org Other Learner",
            role="learner",
            org_id=ORG_ID,
            organization_id=ORG_ID,
            password_hash="not-used",
            avatar_initials="SO",
            gradient_start="#333333",
            gradient_end="#444444",
        ),
        User(
            id=CROSS_ORG_ID,
            username=CROSS_ORG_ID,
            email="learner-lpn-cross@example.edu",
            full_name="Cross Org Learner",
            role="learner",
            org_id=OTHER_ORG_ID,
            organization_id=OTHER_ORG_ID,
            password_hash="not-used",
            avatar_initials="CO",
            gradient_start="#555555",
            gradient_end="#666666",
        ),
    ]
    courses = [
        Course(
            id="lpn-course-1",
            org_id=ORG_ID,
            category_slug="learning-path-notification-org",
            name="Notification Prerequisite",
            slug="notification-prerequisite",
            description="Completed prerequisite",
            status="active",
        ),
        Course(
            id="lpn-course-2",
            org_id=ORG_ID,
            category_slug="learning-path-notification-org",
            name="Unlocked Course",
            slug="unlocked-course",
            description="Course unlocked by path",
            status="active",
        ),
    ]
    path = LearningPath(
        id=PATH_ID,
        org_id=ORG_ID,
        title="Notification Path",
        description="Path used for N5C.1 verification",
        settings="{}",
    )
    db_session.add_all([org, other_org])
    db_session.commit()
    db_session.add_all([*users, *courses, path])
    db_session.flush()
    db_session.add_all(
        [
            LearningPathCourse(path_id=PATH_ID, course_id="lpn-course-1", org_id=ORG_ID, sort_order=1),
            LearningPathCourse(path_id=PATH_ID, course_id="lpn-course-2", org_id=ORG_ID, sort_order=2),
            CourseProgress(
                user_id=LEARNER_ID,
                course_id="lpn-course-1",
                org_id=ORG_ID,
                status="completed",
                completion_percentage=100.0,
                completed_at=datetime.now(timezone.utc),
            ),
        ]
    )
    LearningPathProgressRepository(db_session).assign_path(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()
    return path


def test_learning_path_unlocked_notification_created_once_and_contract_valid(db_session):
    _seed_path(db_session)
    service = LearningPathUnlockService(db_session)

    event = service.evaluate_unlocks(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()

    assert event is not None
    assert event.event_type == "COURSE_UNLOCKED"
    assert event.course_id == "lpn-course-2"

    notifications = db_session.query(Notification).filter_by(
        user_id=LEARNER_ID,
        org_id=ORG_ID,
        type="learning_path_unlocked",
    ).all()
    assert len(notifications) == 1
    notification = notifications[0]
    metadata = notification.metadata_payload()

    assert notification.source_type == "learning_path"
    assert notification.source_id == str(PATH_ID)
    assert metadata["route"] == "/learner/courses"
    assert metadata["route_name"] == "learner_courses"
    assert metadata["path_id"] == PATH_ID
    assert metadata["course_id"] == "lpn-course-2"
    assert metadata["idempotency_key"] == f"{LEARNER_ID}:learning_path_unlocked:{PATH_ID}:lpn-course-2"

    duplicate_event = service.evaluate_unlocks(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()

    assert duplicate_event is None
    assert db_session.query(Notification).filter_by(
        user_id=LEARNER_ID,
        org_id=ORG_ID,
        type="learning_path_unlocked",
    ).count() == 1
    assert db_session.query(LearnerEvent).filter_by(
        user_id=LEARNER_ID,
        org_id=ORG_ID,
        event_type="COURSE_UNLOCKED",
        course_id="lpn-course-2",
    ).count() == 1


def test_learning_path_unlocked_notification_api_unread_read_and_tenant_isolation(db_session):
    _seed_path(db_session)
    db_session.query(Notification).filter_by(
        user_id=LEARNER_ID,
        org_id=ORG_ID,
        type="learning_path_assigned",
    ).update({"is_read": True})
    db_session.commit()
    LearningPathUnlockService(db_session).evaluate_unlocks(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()
    client = _client(db_session)

    unread = client.get("/api/v1/notifications/unread-count")
    assert unread.status_code == 200
    assert unread.json()["count"] == 1

    listing = client.get("/api/v1/notifications")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 2
    notification = next(item for item in items if item["type"] == "learning_path_unlocked")

    assert notification["type"] == "learning_path_unlocked"
    assert notification["source_type"] == "learning_path"
    assert notification["source_id"] == str(PATH_ID)
    assert notification["metadata_json"]["route"] == "/learner/courses"
    assert notification["metadata_json"]["route_name"] == "learner_courses"
    assert notification["metadata_json"]["path_id"] == PATH_ID
    assert notification["metadata_json"]["course_id"] == "lpn-course-2"

    mark_read = client.patch(f"/api/v1/notifications/{notification['id']}/read")
    assert mark_read.status_code == 200
    assert client.get("/api/v1/notifications/unread-count").json()["count"] == 0

    same_org_other = _client(db_session, _learner(SAME_ORG_OTHER_ID, ORG_ID))
    assert same_org_other.get("/api/v1/notifications").json()["items"] == []

    cross_org_other = _client(db_session, _learner(CROSS_ORG_ID, OTHER_ORG_ID))
    assert cross_org_other.get("/api/v1/notifications").json()["items"] == []

    assert db_session.query(Notification).filter(
        Notification.type == "learning_path_unlocked",
        Notification.user_id != LEARNER_ID,
    ).count() == 0
