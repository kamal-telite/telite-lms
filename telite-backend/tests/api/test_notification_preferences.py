import pytest
from app.models.notification_preference import NotificationCategory, OrganizationNotificationDefault, NotificationPreference

@pytest.fixture
def mock_org_default(db_session, test_organization):
    default = OrganizationNotificationDefault(
        org_id=test_organization.id,
        category=NotificationCategory.TASKS.value,
        channel_email=False,
        channel_in_app=True,
    )
    db_session.add(default)
    db_session.commit()
    db_session.refresh(default)
    return default

@pytest.fixture
def test_organization(db_session):
    from app.models.organization import Organization
    org = Organization(name="Test Org", type="b2b", domain="test-org-notif.telite.com", slug="test-org-notif", status="active", plan="enterprise")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture
def test_user(db_session, test_organization):
    from app.models.user import User
    import uuid
    from app.core.password_utils import hash_password
    user = User(
        id=str(uuid.uuid4()),
        email="test_notif@example.com",
        username="test_notif_user",
        password_hash=hash_password("Password123!"),
        full_name="Test User",
        avatar_initials="TU",
        gradient_start="from-blue-500",
        gradient_end="to-blue-600",
        organization_id=test_organization.id,
        org_id=test_organization.id,
        role="learner"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def get_auth_headers(client):
    def _get_headers(user):
        response = client.post(
            "/auth/login",
            data={"username": user.username, "password": "Password123!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _get_headers

def test_get_preferences_system_defaults(client, test_user, get_auth_headers):
    headers = get_auth_headers(test_user)
    resp = client.get("/api/v1/notifications/preferences", headers=headers)
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == len(NotificationCategory)
    
    for pref in data:
        if pref["is_critical"]:
            assert pref["channel_email"] is True
            assert pref["channel_in_app"] is True
            assert pref["source"] == "critical"
        else:
            assert pref["channel_email"] is True
            assert pref["channel_in_app"] is True
            assert pref["source"] == "system"

def test_get_preferences_org_defaults(client, test_user, get_auth_headers, mock_org_default):
    headers = get_auth_headers(test_user)
    resp = client.get("/api/v1/notifications/preferences", headers=headers)
    
    assert resp.status_code == 200
    data = resp.json()
    
    tasks_pref = next(p for p in data if p["category"] == NotificationCategory.TASKS.value)
    assert tasks_pref["channel_email"] is False
    assert tasks_pref["channel_in_app"] is True
    assert tasks_pref["source"] == "org"
    
    courses_pref = next(p for p in data if p["category"] == NotificationCategory.COURSES.value)
    assert courses_pref["channel_email"] is True
    assert courses_pref["source"] == "system"

def test_patch_preference_user_override(client, db_session, test_user, get_auth_headers, mock_org_default):
    headers = get_auth_headers(test_user)
    resp = client.patch(
        f"/api/v1/notifications/preferences/{NotificationCategory.TASKS.value}",
        headers=headers,
        json={"channel_email": True, "channel_in_app": False}
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == NotificationCategory.TASKS.value
    assert data["channel_email"] is True
    assert data["channel_in_app"] is False
    assert data["source"] == "user"
    
    db_pref = db_session.query(NotificationPreference).filter_by(
        user_id=test_user.id, category=NotificationCategory.TASKS.value
    ).first()
    assert db_pref is not None
    assert db_pref.channel_email is True
    assert db_pref.channel_in_app is False

def test_patch_preference_critical_bypass(client, test_user, get_auth_headers):
    headers = get_auth_headers(test_user)
    resp = client.patch(
        f"/api/v1/notifications/preferences/{NotificationCategory.SECURITY.value}",
        headers=headers,
        json={"channel_email": False, "channel_in_app": False}
    )
    
    assert resp.status_code == 403
    assert "critical security" in resp.json()["detail"]

def test_patch_preference_invalid_category(client, test_user, get_auth_headers):
    headers = get_auth_headers(test_user)
    resp = client.patch(
        "/api/v1/notifications/preferences/invalid_cat",
        headers=headers,
        json={"channel_email": False}
    )
    
    assert resp.status_code == 400
    assert "Invalid notification category" in resp.json()["detail"]

def test_multi_tenant_isolation(client, db_session, test_user, get_auth_headers):
    headers = get_auth_headers(test_user)
    client.patch(
        f"/api/v1/notifications/preferences/{NotificationCategory.COURSES.value}",
        headers=headers,
        json={"channel_email": False, "channel_in_app": False}
    )
    
    db_pref = db_session.query(NotificationPreference).filter_by(
        user_id=test_user.id, category=NotificationCategory.COURSES.value
    ).first()
    assert db_pref.org_id == test_user.org_id
