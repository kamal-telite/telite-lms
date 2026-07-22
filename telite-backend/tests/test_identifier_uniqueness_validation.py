import pytest
from uuid import uuid4

from app.models.user import User
from app.models.organization import Organization
from app.repositories.user_repo import UserRepository, IdentifierCollisionError

def _create_user(db_session, email: str, username: str) -> str:
    # Ensure organization exists
    if not db_session.get(Organization, 1):
        org = Organization(id=1, name="Test Org", domain="test.com", slug="test", type="b2b")
        db_session.add(org)
        db_session.flush()

    user_id = str(uuid4())
    user = User(
        id=user_id,
        email=email.strip().lower(),
        username=username.strip().lower(),
        full_name="Test User",
        status="active",
        org_id=1,
        role="learner",
        password_hash="fakehash",
        avatar_initials="TU",
        gradient_start="#000000",
        gradient_end="#ffffff",
    )
    db_session.add(user)
    db_session.commit()
    return user_id

def test_validate_identifier_uniqueness_no_conflicts(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "user1@example.com", "user1")
    
    # Should not raise any exception
    repo.validate_identifier_uniqueness("user2@example.com", "user2")

def test_validate_identifier_uniqueness_email_collision(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "target@example.com", "target")
    
    with pytest.raises(IdentifierCollisionError) as exc:
        repo.validate_identifier_uniqueness("target@example.com", "new_user")
    assert "target@example.com" in str(exc.value)

def test_validate_identifier_uniqueness_username_collision(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "target@example.com", "target_username")
    
    with pytest.raises(IdentifierCollisionError) as exc:
        repo.validate_identifier_uniqueness("new@example.com", "target_username")
    assert "target_username" in str(exc.value)

def test_validate_identifier_uniqueness_cross_column_email_to_username(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "user1@example.com", "weird_username@example.com")
    
    # New user wants to use "weird_username@example.com" as their email, but it's taken as a username
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("weird_username@example.com", "new_user")

def test_validate_identifier_uniqueness_cross_column_username_to_email(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "target@example.com", "target")
    
    # New user wants to use "target@example.com" as their username, but it's taken as an email
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("new@example.com", "target@example.com")

def test_validate_identifier_uniqueness_case_insensitive(db_session):
    repo = UserRepository(db_session)
    _create_user(db_session, "CamelCase@Example.com", "CamelUser")
    
    # Check lowercase version
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("camelcase@example.com", "new_user")
        
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("new@example.com", "cameluser")

def test_validate_identifier_uniqueness_exclude_user_id_allows_own_identifiers(db_session):
    repo = UserRepository(db_session)
    user_id = _create_user(db_session, "myemail@example.com", "myusername")
    
    # Update should pass since it excludes this user's ID
    repo.validate_identifier_uniqueness("myemail@example.com", "myusername", exclude_user_id=user_id)

def test_validate_identifier_uniqueness_exclude_user_id_blocks_other_identifiers(db_session):
    repo = UserRepository(db_session)
    user_id = _create_user(db_session, "myemail@example.com", "myusername")
    other_user_id = _create_user(db_session, "taken@example.com", "takenusername")
    
    # Update trying to steal other's email
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("taken@example.com", "myusername", exclude_user_id=user_id)
        
    # Update trying to steal other's username
    with pytest.raises(IdentifierCollisionError):
        repo.validate_identifier_uniqueness("myemail@example.com", "takenusername", exclude_user_id=user_id)
