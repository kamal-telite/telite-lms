from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.learning_path import LearningPath
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.user import User
from app.repositories.learning_path_progress_repo import LearningPathProgressRepository


ORG_ID = 81
OTHER_ORG_ID = 82
LEARNER_ID = "learner-lpa-1"
SAME_ORG_OTHER_ID = "learner-lpa-2"
CROSS_ORG_ID = "learner-lpa-cross"
PATH_ID = 8101


def _learner(user_id: str = LEARNER_ID, org_id: int = ORG_ID) -> TokenData:
    return TokenData(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
        full_name=f"{user_id} Name",
        role="learner",
        org_id=org_id,
    )


def _client(session, user: TokenData | None = None) -> TestClient:
    app = create_app()

    def override_user():
        return user or _learner()

    def override_db_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = override_db_session
    return TestClient(app)


def _seed_path(session) -> LearningPath:
    session.add_all(
        [
            Organization(
                id=ORG_ID,
                name="Learning Path Assignment Notification Org",
                type="company",
                domain="learning-path-assignment.example.edu",
                slug="learning-path-assignment-org",
                status="active",
                plan="free",
            ),
            Organization(
                id=OTHER_ORG_ID,
                name="Other Learning Path Assignment Notification Org",
                type="company",
                domain="other-learning-path-assignment.example.edu",
                slug="other-learning-path-assignment-org",
                status="active",
                plan="free",
            ),
        ]
    )
    session.commit()
    session.add_all(
        [
            User(
                id=LEARNER_ID,
                username=LEARNER_ID,
                email="learner-lpa-1@example.edu",
                full_name="Assignment Notification Learner",
                role="learner",
                org_id=ORG_ID,
                organization_id=ORG_ID,
                password_hash="not-used",
                avatar_initials="LA",
                gradient_start="#111111",
                gradient_end="#222222",
            ),
            User(
                id=SAME_ORG_OTHER_ID,
                username=SAME_ORG_OTHER_ID,
                email="learner-lpa-2@example.edu",
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
                email="learner-lpa-cross@example.edu",
                full_name="Cross Org Learner",
                role="learner",
                org_id=OTHER_ORG_ID,
                organization_id=OTHER_ORG_ID,
                password_hash="not-used",
                avatar_initials="CO",
                gradient_start="#555555",
                gradient_end="#666666",
            ),
            LearningPath(
                id=PATH_ID,
                org_id=ORG_ID,
                title="Assignment Notification Path",
                description="Path used for N5C.2 verification",
                settings="{}",
            ),
        ]
    )
    session.commit()
    return session.get(LearningPath, PATH_ID)


def test_learning_path_assignment_notification_created_once_and_contract_valid(db_session):
    _seed_path(db_session)
    repo = LearningPathProgressRepository(db_session)

    progress, created = repo.assign_path(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()
    duplicate, duplicate_created = repo.assign_path(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == progress.id

    notifications = db_session.query(Notification).filter_by(
        user_id=LEARNER_ID,
        org_id=ORG_ID,
        type="learning_path_assigned",
    ).all()
    assert len(notifications) == 1
    notification = notifications[0]
    metadata = notification.metadata_payload()

    assert notification.source_type == "learning_path"
    assert notification.source_id == str(PATH_ID)
    assert metadata["route"] == "/learner/paths"
    assert metadata["route_name"] == "learner_paths"
    assert metadata["path_id"] == PATH_ID
    assert metadata["idempotency_key"] == f"{LEARNER_ID}:learning_path_assigned:{PATH_ID}"


def test_learning_path_assignment_notification_api_unread_read_and_tenant_isolation(db_session):
    _seed_path(db_session)
    LearningPathProgressRepository(db_session).assign_path(LEARNER_ID, PATH_ID, ORG_ID)
    db_session.commit()
    client = _client(db_session)

    assert client.get("/api/v1/notifications/unread-count").json()["count"] == 1

    listing = client.get("/api/v1/notifications")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    notification = items[0]
    assert notification["type"] == "learning_path_assigned"
    assert notification["source_type"] == "learning_path"
    assert notification["source_id"] == str(PATH_ID)
    assert notification["metadata_json"]["route"] == "/learner/paths"
    assert notification["metadata_json"]["route_name"] == "learner_paths"

    assert client.patch(f"/api/v1/notifications/{notification['id']}/read").status_code == 200
    assert client.get("/api/v1/notifications/unread-count").json()["count"] == 0

    same_org_other = _client(db_session, _learner(SAME_ORG_OTHER_ID, ORG_ID))
    assert same_org_other.get("/api/v1/notifications").json()["items"] == []

    cross_org_other = _client(db_session, _learner(CROSS_ORG_ID, OTHER_ORG_ID))
    assert cross_org_other.get("/api/v1/notifications").json()["items"] == []

    assert db_session.query(Notification).filter(
        Notification.type == "learning_path_assigned",
        Notification.user_id != LEARNER_ID,
    ).count() == 0
