import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.organization import Organization
from app.repositories.audit_repo import AuditLog
from app.core.password_utils import verify_password
import uuid

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

@pytest.fixture
def setup_tenants_and_users(db_session: Session):
    org1 = Organization(id=1, slug="org1", name="Org 1", type="internal", domain="org1.com")
    org2 = Organization(id=2, slug="org2", name="Org 2", type="internal", domain="org2.com")
    db_session.add_all([org1, org2])
    
    from app.core.password_utils import hash_password
    
    user1 = User(
        id=f"user-{uuid.uuid4().hex[:12]}",
        org_id=1,
        username="user1",
        email="user1@example.com",
        full_name="User One",
        role="learner",
        password_hash=hash_password("Password123!"),
        avatar_initials="UO",
        gradient_start="#000",
        gradient_end="#fff"
    )
    user2 = User(
        id=f"user-{uuid.uuid4().hex[:12]}",
        org_id=2,
        username="user2",
        email="user2@example.com",
        full_name="User Two",
        role="learner",
        password_hash=hash_password("Password123!"),
        avatar_initials="UT",
        gradient_start="#000",
        gradient_end="#fff"
    )
    db_session.add_all([user1, user2])
    db_session.commit()
    return user1, user2

def test_successful_profile_update(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, _ = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.patch(
        "/auth/me",
        headers=headers,
        json={
            "full_name": "Updated User One",
            "email": "updated1@example.com",
            "username": "updated_user1",
            "avatar": "UU"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"]["full_name"] == "Updated User One"
    assert data["user"]["email"] == "updated1@example.com"
    assert data["user"]["username"] == "updated_user1"
    
    db_session.expire_all()
    db_user = db_session.query(User).filter(User.id == user1.id).first()
    assert db_user.full_name == "Updated User One"
    assert db_user.email == "updated1@example.com"
    assert db_user.username == "updated_user1"

    audit_log = db_session.query(AuditLog).filter(
        AuditLog.actor_user_id == user1.id,
        AuditLog.action == "user.update_profile"
    ).first()
    assert audit_log is not None

def test_duplicate_email(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, user2 = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.patch(
        "/auth/me",
        headers=headers,
        json={"email": user2.email}
    )
    assert response.status_code == 409
    assert "Identifier" in response.json()["detail"]

def test_duplicate_username(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, user2 = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.patch(
        "/auth/me",
        headers=headers,
        json={"username": user2.username}
    )
    assert response.status_code == 409
    assert "Identifier" in response.json()["detail"]

def test_multi_tenant_isolation_uniqueness(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, user2 = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.patch(
        "/auth/me",
        headers=headers,
        json={"email": user2.email}
    )
    assert response.status_code == 409

def test_password_change_success(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, _ = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.post(
        "/auth/me/password",
        headers=headers,
        json={
            "current_password": "Password123!",
            "new_password": "NewStrongPassword1!"
        }
    )
    assert response.status_code == 200
    assert "Please log in again" in response.json()["message"]
    
    set_cookie = response.headers.get("set-cookie", "")
    assert 'telite_access_token="";' in set_cookie or "telite_access_token=;" in set_cookie or "Max-Age=0" in set_cookie
    
    db_session.expire_all()
    db_user = db_session.query(User).filter(User.id == user1.id).first()
    assert verify_password("NewStrongPassword1!", db_user.password_hash)

    audit_log = db_session.query(AuditLog).filter(
        AuditLog.actor_user_id == user1.id,
        AuditLog.action == "user.update_password"
    ).first()
    assert audit_log is not None

def test_incorrect_current_password(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, _ = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.post(
        "/auth/me/password",
        headers=headers,
        json={
            "current_password": "WrongPassword!",
            "new_password": "NewStrongPassword1!"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect current password"

def test_weak_password_enforcement(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, _ = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    response = client.post(
        "/auth/me/password",
        headers=headers,
        json={
            "current_password": "Password123!",
            "new_password": "weak"
        }
    )
    assert response.status_code == 400
    assert "at least 8 characters long" in response.json()["detail"]

def test_jwt_behavior_after_identifier_changes(client: TestClient, db_session: Session, setup_tenants_and_users, get_auth_headers):
    user1, _ = setup_tenants_and_users
    headers = get_auth_headers(user1)
    
    client.patch(
        "/auth/me",
        headers=headers,
        json={"email": "newemail999@example.com"}
    )
    
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "newemail999@example.com"
