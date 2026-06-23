from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import TokenData, get_current_user
from app.db.engine import db_session
from app.main import create_app
from app.models.announcement import Announcement, AnnouncementReadState
from app.models.organization import Organization
from app.models.user import User


ORG_ID = 91
OTHER_ORG_ID = 92
ADMIN_ID = "announcement-admin"
LEARNER_ID = "announcement-learner"
OTHER_LEARNER_ID = "announcement-other-learner"
CROSS_ORG_LEARNER_ID = "announcement-cross-learner"


def _token(
    user_id: str,
    *,
    role: str = "learner",
    org_id: int = ORG_ID,
    category_scope: str | None = "science",
) -> TokenData:
    return TokenData(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
        full_name=f"{user_id} Name",
        role=role,
        org_id=org_id,
        category_scope=category_scope,
    )


def _client(session, user: TokenData) -> TestClient:
    app = create_app()

    def override_user():
        return user

    def override_db_session():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[db_session] = override_db_session
    return TestClient(app)


def _seed(session) -> None:
    session.add_all(
        [
            Organization(
                id=ORG_ID,
                name="Announcement Runtime Org",
                type="college",
                domain="announcement-runtime.example.edu",
                slug="announcement-runtime-org",
                status="active",
                plan="free",
            ),
            Organization(
                id=OTHER_ORG_ID,
                name="Other Announcement Runtime Org",
                type="college",
                domain="other-announcement-runtime.example.edu",
                slug="other-announcement-runtime-org",
                status="active",
                plan="free",
            ),
        ]
    )
    session.commit()
    session.add_all(
        [
            User(
                id=ADMIN_ID,
                username=ADMIN_ID,
                email="announcement-admin@example.edu",
                full_name="Announcement Admin",
                role="category_admin",
                category_scope="science",
                org_id=ORG_ID,
                organization_id=ORG_ID,
                password_hash="not-used",
                avatar_initials="AA",
                gradient_start="#111111",
                gradient_end="#222222",
            ),
            User(
                id=LEARNER_ID,
                username=LEARNER_ID,
                email="announcement-learner@example.edu",
                full_name="Announcement Learner",
                role="learner",
                category_scope="science",
                org_id=ORG_ID,
                organization_id=ORG_ID,
                password_hash="not-used",
                avatar_initials="AL",
                gradient_start="#333333",
                gradient_end="#444444",
            ),
            User(
                id=OTHER_LEARNER_ID,
                username=OTHER_LEARNER_ID,
                email="announcement-other-learner@example.edu",
                full_name="Other Announcement Learner",
                role="learner",
                category_scope="math",
                org_id=ORG_ID,
                organization_id=ORG_ID,
                password_hash="not-used",
                avatar_initials="OL",
                gradient_start="#555555",
                gradient_end="#666666",
            ),
            User(
                id=CROSS_ORG_LEARNER_ID,
                username=CROSS_ORG_LEARNER_ID,
                email="announcement-cross-learner@example.edu",
                full_name="Cross Org Announcement Learner",
                role="learner",
                category_scope="science",
                org_id=OTHER_ORG_ID,
                organization_id=OTHER_ORG_ID,
                password_hash="not-used",
                avatar_initials="CO",
                gradient_start="#777777",
                gradient_end="#888888",
            ),
        ]
    )
    session.commit()


def test_announcement_admin_crud_and_tenant_isolation(db_session):
    _seed(db_session)
    admin_client = _client(db_session, _token(ADMIN_ID, role="category_admin"))

    created = admin_client.post(
        "/api/v1/announcements",
        json={
            "title": "Exam Window",
            "body": "The exam window opens Monday.",
            "audience_type": "all",
            "status": "published",
        },
    )
    assert created.status_code == 200
    announcement_id = created.json()["id"]
    assert created.json()["audiences"][0]["audience_type"] == "all"

    listing = admin_client.get("/api/v1/announcements")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    updated = admin_client.patch(
        f"/api/v1/announcements/{announcement_id}",
        json={"title": "Updated Exam Window", "audience_type": "category", "audience_value": "science"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Exam Window"
    assert updated.json()["audiences"][0]["audience_type"] == "category"

    cross_admin = _client(db_session, _token("cross-admin", role="category_admin", org_id=OTHER_ORG_ID))
    assert cross_admin.get(f"/api/v1/announcements/{announcement_id}").status_code == 404
    assert cross_admin.get("/api/v1/announcements").json()["items"] == []

    deleted = admin_client.delete(f"/api/v1/announcements/{announcement_id}")
    assert deleted.status_code == 200
    assert db_session.query(Announcement).filter_by(id=announcement_id).count() == 0


def test_announcement_audience_scoping_and_read_state(db_session):
    _seed(db_session)
    admin_client = _client(db_session, _token(ADMIN_ID, role="category_admin"))
    learner_client = _client(db_session, _token(LEARNER_ID, category_scope="science"))
    other_client = _client(db_session, _token(OTHER_LEARNER_ID, category_scope="math"))
    cross_client = _client(db_session, _token(CROSS_ORG_LEARNER_ID, org_id=OTHER_ORG_ID, category_scope="science"))

    all_announcement = admin_client.post(
        "/api/v1/announcements",
        json={"title": "All Hands", "body": "Visible to everyone.", "audience_type": "all"},
    ).json()
    category_announcement = admin_client.post(
        "/api/v1/announcements",
        json={
            "title": "Science Lab",
            "body": "Visible to science.",
            "audience_type": "category",
            "audience_value": "science",
        },
    ).json()
    role_announcement = admin_client.post(
        "/api/v1/announcements",
        json={"title": "Learner Notice", "body": "Visible to learners.", "audience_type": "role", "audience_value": "learner"},
    ).json()
    user_announcement = admin_client.post(
        "/api/v1/announcements",
        json={"title": "Private Notice", "body": "Visible to one learner.", "audience_type": "user", "audience_value": LEARNER_ID},
    ).json()

    learner_items = learner_client.get("/api/v1/announcements/my").json()["items"]
    learner_titles = {item["title"] for item in learner_items}
    assert learner_titles == {"All Hands", "Science Lab", "Learner Notice", "Private Notice"}
    assert all(item["is_read"] is False for item in learner_items)

    other_titles = {item["title"] for item in other_client.get("/api/v1/announcements/my").json()["items"]}
    assert other_titles == {"All Hands", "Learner Notice"}
    assert cross_client.get("/api/v1/announcements/my").json()["items"] == []

    mark_read = learner_client.patch(f"/api/v1/announcements/{category_announcement['id']}/read")
    assert mark_read.status_code == 200
    repeat_read = learner_client.patch(f"/api/v1/announcements/{category_announcement['id']}/read")
    assert repeat_read.status_code == 200
    assert db_session.query(AnnouncementReadState).filter_by(
        announcement_id=category_announcement["id"],
        user_id=LEARNER_ID,
        org_id=ORG_ID,
    ).count() == 1

    refreshed = learner_client.get("/api/v1/announcements/my").json()["items"]
    read_item = next(item for item in refreshed if item["id"] == category_announcement["id"])
    assert read_item["is_read"] is True
    assert read_item["read_at"] is not None

    hidden = other_client.patch(f"/api/v1/announcements/{user_announcement['id']}/read")
    assert hidden.status_code == 404
    assert {all_announcement["id"], role_announcement["id"], category_announcement["id"], user_announcement["id"]}
