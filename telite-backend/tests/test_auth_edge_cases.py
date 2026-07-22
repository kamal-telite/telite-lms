import pytest
from sqlalchemy import text
from app.repositories.user_repo import UserRepository, IdentifierCollisionError
from app.api.auth import authenticate_user
from fastapi import HTTPException
from app.core.password_utils import hash_password
from app.models.user import User

@pytest.fixture
def auth_test_db(db_session):
    # Setup roles and an org for tests
    db_session.execute(text("TRUNCATE TABLE users CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE organizations CASCADE;"))
    db_session.execute(text("INSERT INTO organizations (id, name, type, domain, slug, status, plan) VALUES (1, 'Test Org', 'company', 'test.com', 'test-org', 'active', 'pro');"))
    db_session.execute(text("INSERT INTO organizations (id, name, type, domain, slug, status, plan) VALUES (2, 'Other Org', 'company', 'other.com', 'other-org', 'active', 'pro');"))
    db_session.commit()
    yield db_session
    db_session.execute(text("TRUNCATE TABLE users CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE organizations CASCADE;"))
    db_session.commit()

def test_login_by_email_and_username(auth_test_db):
    repo = UserRepository(auth_test_db)
    user = repo.create_user(
        email="normal@test.com",
        username="normaluser",
        full_name="Normal User",
        role="learner",
        org_id=1,
        password="Password123!"
    )
    
    # Login by email
    auth_email = authenticate_user(auth_test_db, "normal@test.com", "Password123!")
    assert auth_email.id == user.id
    
    # Login by username
    auth_user = authenticate_user(auth_test_db, "normaluser", "Password123!")
    assert auth_user.id == user.id

def test_login_invalid_credentials(auth_test_db):
    repo = UserRepository(auth_test_db)
    repo.create_user(
        email="valid@test.com",
        username="validuser",
        full_name="Valid",
        role="learner",
        org_id=1,
        password="Password123!"
    )
    
    with pytest.raises(HTTPException) as exc:
        authenticate_user(auth_test_db, "invalid@test.com", "Password123!")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        authenticate_user(auth_test_db, "validuser", "WrongPassword!")
    assert exc.value.status_code == 401

def test_cross_column_collision_deterministic_login(auth_test_db):
    # Simulate a DB-level cross-column collision via raw SQL (e.g. from bad migration)
    from app.models.user import User
    u1 = User(
        id='user-1', username='conflict@test.com', email='user1@test.com', 
        password_hash=hash_password("Password123!"), full_name='User 1', 
        role='learner', is_active=True, status='active', org_id=1, 
        avatar_initials='U1', gradient_start='#0', gradient_end='#0'
    )
    u2 = User(
        id='user-2', username='user2', email='conflict@test.com', 
        password_hash=hash_password("Password123!"), full_name='User 2', 
        role='learner', is_active=True, status='active', org_id=1, 
        avatar_initials='U2', gradient_start='#0', gradient_end='#0'
    )
    auth_test_db.add_all([u1, u2])
    auth_test_db.commit()
    
    # Login with the conflicting identifier
    # Deterministic lookup checks Email first, so it should log in User 2
    auth_user = authenticate_user(auth_test_db, "conflict@test.com", "Password123!")
    assert auth_user.id == 'user-2'
    
    # User 1 can still log in with their actual email
    auth_user1 = authenticate_user(auth_test_db, "user1@test.com", "Password123!")
    assert auth_user1.id == 'user-1'

def test_create_user_prevents_duplicate_rejection(auth_test_db):
    repo = UserRepository(auth_test_db)
    repo.create_user(email="dup@test.com", username="dupuser", full_name="Dup", role="learner", org_id=1)
    
    with pytest.raises(IdentifierCollisionError):
        repo.create_user(email="dup@test.com", username="other", full_name="Other", role="learner", org_id=1)
        
    with pytest.raises(IdentifierCollisionError):
        repo.create_user(email="other@test.com", username="dupuser", full_name="Other", role="learner", org_id=1)

def test_create_user_prevents_cross_column_rejection(auth_test_db):
    repo = UserRepository(auth_test_db)
    repo.create_user(email="a@test.com", username="a_user", full_name="A", role="learner", org_id=1)
    
    # Try to create User B with username matching User A's email
    with pytest.raises(IdentifierCollisionError):
        repo.create_user(email="b@test.com", username="a@test.com", full_name="B", role="learner", org_id=1)

    # Try to create User C with email matching User A's username
    with pytest.raises(IdentifierCollisionError):
        repo.create_user(email="a_user", username="c_user", full_name="C", role="learner", org_id=1)

def test_update_user_collision(auth_test_db):
    repo = UserRepository(auth_test_db)
    user1 = repo.create_user(email="u1@test.com", username="u1", full_name="U1", role="learner", org_id=1)
    user2 = repo.create_user(email="u2@test.com", username="u2", full_name="U2", role="learner", org_id=1)
    
    with pytest.raises(IdentifierCollisionError):
        repo.update(user2, email="u1")
        
    with pytest.raises(IdentifierCollisionError):
        repo.update(user2, username="u1@test.com")
        
    # Updating self should not throw error
    repo.update(user1, email="u1@test.com")

def test_inactive_and_suspended_users(auth_test_db):
    repo = UserRepository(auth_test_db)
    user = repo.create_user(
        email="inactive@test.com",
        username="inactive",
        full_name="Inactive",
        role="learner",
        org_id=1,
        password="Password123!"
    )
    repo.set_active(user, is_active=False)
    
    with pytest.raises(HTTPException) as exc:
        authenticate_user(auth_test_db, "inactive@test.com", "Password123!")
    assert exc.value.status_code == 401

def test_multi_tenant_login(auth_test_db):
    repo = UserRepository(auth_test_db)
    # User in Org 1
    u1 = repo.create_user(email="org1@test.com", username="org1user", full_name="Org 1", role="learner", org_id=1, password="PW")
    # User in Org 2
    u2 = repo.create_user(email="org2@test.com", username="org2user", full_name="Org 2", role="learner", org_id=2, password="PW")
    
    auth_u1 = authenticate_user(auth_test_db, "org1@test.com", "PW")
    assert auth_u1.id == u1.id
    assert auth_u1.org_id == 1
    
    auth_u2 = authenticate_user(auth_test_db, "org2user", "PW")
    assert auth_u2.id == u2.id
    assert auth_u2.org_id == 2

def test_get_by_identifier_for_auth_translates_multiple_results(auth_test_db):
    from app.repositories.user_repo import UserRepository, IdentifierCollisionError
    from sqlalchemy.exc import MultipleResultsFound
    from unittest.mock import patch, MagicMock
    
    repo = UserRepository(auth_test_db)
    
    # Mock session.execute to return a mock result whose scalar_one_or_none raises MultipleResultsFound
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = MultipleResultsFound("Mock collision")
    
    with patch.object(auth_test_db, 'execute', return_value=mock_result):
        with pytest.raises(IdentifierCollisionError):
            repo.get_by_identifier_for_auth("same@test.com")

def test_multiple_results_found_graceful_handling(auth_test_db):
    from unittest.mock import patch
    from app.repositories.user_repo import IdentifierCollisionError
    
    with patch('app.repositories.user_repo.UserRepository.get_by_identifier_for_auth', side_effect=IdentifierCollisionError("Ambiguous identifier collision")):
        with pytest.raises(HTTPException) as exc:
            authenticate_user(auth_test_db, "same@test.com", "PW")
        assert exc.value.status_code == 401
        assert exc.value.detail == "Incorrect username or password"
