import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime

from app.models.organization import Organization
from app.models.user import User
from app.models.category import Category
from app.main import app
from app.api.auth import get_current_user

# Mock tokens and users
def override_get_current_user(org_id=1, role="super_admin", user_id="admin-1"):
    from app.api.auth import TokenData
    return TokenData(
        id=user_id,
        email=f"admin{org_id}@example.com",
        role=role,
        full_name=f"Admin Org {org_id}",
        org_id=org_id,
        is_platform_admin=False,
    )

@pytest.fixture
def org_admin_client(db_session: Session):
    # Setup test data
    org1 = Organization(id=1, name="Test Org 1", slug="test-org-1", type="college", domain="org1.com")
    org2 = Organization(id=2, name="Test Org 2", slug="test-org-2", type="college", domain="org2.com")
    db_session.add_all([org1, org2])
    db_session.commit()

    # Admin User
    admin = User(
        id="admin-1",
        email="admin1@example.com",
        username="admin1",
        full_name="Admin Org 1",
        role="super_admin",
        org_id=1,
        password_hash="test",
        avatar_initials="A1",
        gradient_start="",
        gradient_end="",
        is_active=True,
        status="active"
    )

    # User in Org 1 (same org)
    u1 = User(
        id="user-org1-1",
        email="learner@org1.com",
        username="learner-org1",
        full_name="Learner 1",
        role="learner",
        org_id=1,
        password_hash="test",
        avatar_initials="L1",
        gradient_start="",
        gradient_end="",
        is_active=True,
    )
    # User in Org 2 (different org)
    u2 = User(
        id="user-org2-1",
        email="learner@org2.com",
        username="learner-org2",
        full_name="Learner 2",
        role="learner",
        org_id=2,
        password_hash="test",
        avatar_initials="L2",
        gradient_start="",
        gradient_end="",
        is_active=True,
    )
    # Platform Admin
    u_plat = User(
        id="user-plat-1",
        email="platadmin@system.com",
        username="platadmin",
        full_name="Plat Admin",
        role="platform_admin",
        org_id=1,
        is_platform_admin=True,
        password_hash="test",
        avatar_initials="PA",
        gradient_start="",
        gradient_end="",
        is_active=True,
    )
    # Archived User in Org 1
    u_archived = User(
        id="user-archived-1",
        email="archived@org1.com",
        username="archived",
        full_name="Archived",
        role="learner",
        org_id=1,
        is_active=False,
        status="disabled",
        password_hash="test",
        avatar_initials="AR",
        gradient_start="",
        gradient_end="",
    )
    db_session.add_all([admin, u1, u2, u_plat, u_archived])
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: override_get_current_user(org_id=1, role="super_admin")
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    
    # Cleanup
    db_session.delete(admin)
    db_session.delete(u1)
    db_session.delete(u2)
    db_session.delete(u_plat)
    db_session.delete(u_archived)
    db_session.delete(org1)
    db_session.delete(org2)
    db_session.commit()

def test_promote_admin_same_org(org_admin_client, db_session):
    response = org_admin_client.post("/admins?orgId=1", json={
        "email": "learner@org1.com",
        "role": "category_admin",
        "full_name": "Learner 1",
        "category_scope": "tech"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "learner@org1.com"

def test_promote_admin_different_org(org_admin_client, db_session):
    response = org_admin_client.post("/admins?orgId=1", json={
        "email": "learner@org2.com",
        "role": "category_admin",
        "full_name": "Learner 2",
        "category_scope": "tech"
    })
    assert response.status_code == 403
    assert "belongs to another organization" in response.json()["detail"]

def test_promote_platform_admin(org_admin_client, db_session):
    response = org_admin_client.post("/admins?orgId=1", json={
        "email": "platadmin@system.com",
        "role": "category_admin",
        "full_name": "Plat Admin",
        "category_scope": "tech"
    })
    assert response.status_code == 403
    assert "Cannot modify platform administrator" in response.json()["detail"]

def test_promote_archived_user(org_admin_client, db_session):
    response = org_admin_client.post("/admins?orgId=1", json={
        "email": "archived@org1.com",
        "role": "category_admin",
        "full_name": "Archived",
        "category_scope": "tech"
    })
    assert response.status_code == 403
    assert "Cannot modify an archived or inactive user" in response.json()["detail"]

def test_hard_deletion_is_now_soft_delete(org_admin_client, db_session):
    response = org_admin_client.delete("/users/user-org1-1")
    assert response.status_code == 200
    
    # Verify in DB that it is softly deleted
    from sqlalchemy import select
    user = db_session.execute(select(User).where(User.id == "user-org1-1")).scalar_one()
    assert user.is_active is False
    assert user.status == "disabled"
