import pytest
import hashlib
from sqlalchemy import text
from app.repositories.user_repo import UserRepository

@pytest.fixture
def auth_test_db(db_session):
    db_session.execute(text("TRUNCATE TABLE users CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE organizations CASCADE;"))
    db_session.execute(text("INSERT INTO organizations (id, name, type, domain, slug, status, plan) VALUES (1, 'Test Org', 'company', 'test.com', 'test-org', 'active', 'pro');"))
    db_session.commit()
    yield db_session
    db_session.execute(text("TRUNCATE TABLE users CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE organizations CASCADE;"))
    db_session.commit()

@pytest.fixture
def auth_users(auth_test_db):
    repo = UserRepository(auth_test_db)
    user1 = repo.create_user(
        email="user1@test.com",
        username="user1",
        full_name="User One",
        role="learner",
        org_id=1,
        password="Password123!"
    )
    user2 = repo.create_user(
        email="user2@test.com",
        username="user2",
        full_name="User Two",
        role="learner",
        org_id=1,
        password="Password123!"
    )
    auth_test_db.commit()
    return user1, user2

def test_add_account_success(client, auth_users):
    user1, user2 = auth_users
    
    # 1. Login to the primary account
    res1 = client.post("/auth/login", data={
        "username": "user1",
        "password": "Password123!"
    })
    assert res1.status_code == 200
    
    
    # Check that cookies are set
    cookies = client.cookies
    cookie_name_1 = f"telite_account_refresh_{hashlib.sha256(user1.id.encode()).hexdigest()[:20]}"
    assert cookie_name_1 in cookies
    
    # 2. Add second account
    res2 = client.post("/auth/sessions/add-account", json={
        "username": "user2",
        "password": "Password123!"
    })
    assert res2.status_code == 200
    assert res2.json()["status"] == "account_added"
    assert res2.json()["user_id"] == user2.id
    
    # Check that second cookie is set
    cookies = client.cookies
    cookie_name_2 = f"telite_account_refresh_{hashlib.sha256(user2.id.encode()).hexdigest()[:20]}"
    assert cookie_name_2 in cookies

def test_add_account_invalid_credentials(client, auth_users):
    res = client.post("/auth/sessions/add-account", json={
        "username": "user2",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]

def test_add_account_invalid_user(client, auth_users):
    res = client.post("/auth/sessions/add-account", json={
        "username": "nonexistent",
        "password": "Password123!"
    })
    assert res.status_code == 401
    assert "Invalid credentials" in res.json()["detail"]

def test_add_account_sets_all_required_cookies(client, auth_users):
    user1, _ = auth_users
    
    # Login first
    client.post("/auth/login", data={
        "username": "user1",
        "password": "Password123!"
    })
    
    res = client.post("/auth/sessions/add-account", json={
        "username": "user1",
        "password": "Password123!"
    })
    assert res.status_code == 200
    
    # Ensure standard auth cookies are also refreshed/set
    assert "telite_access_token" in client.cookies
    assert "telite_refresh_token" in client.cookies
    cookie_name_1 = f"telite_account_refresh_{hashlib.sha256(user1.id.encode()).hexdigest()[:20]}"
    assert cookie_name_1 in client.cookies
