from sqlalchemy import text
from app.api.auth import authenticate_user
from app.repositories.user_repo import UserRepository
from app.db.rls import apply_rls_policies

def test_login_rls_bypass(db_session):
    # Enable RLS policies because conftest.py's Base.metadata.create_all does not create them
    apply_rls_policies(db_session)
    db_session.commit()

    # Setup: Create org and user while explicitly bypassing RLS
    db_session.execute(text("SET LOCAL app.bypass_rls = 'on'"))
    
    db_session.execute(text(
        "INSERT INTO organizations (id, name, type, domain, slug, status, plan) "
        "VALUES (1, 'Test Org', 'company', 'test.local', 'test-org', 'active', 'test')"
    ))
    
    repo = UserRepository(db_session)
    repo.create_user(
        email="globaladmin@ktlearn.local",
        full_name="Global Admin",
        role="platform_admin",
        org_id=1,
        password="GlobalAdmin@1234",
        username="globaladmin",
        is_platform_admin=True
    )
    db_session.commit()
    
    # Restore normal RLS context
    db_session.execute(text("SET LOCAL app.bypass_rls = 'off'"))

    # Test 1: Authentication succeeds (bypasses RLS internally)
    try:
        user = authenticate_user(db_session, "globaladmin", "GlobalAdmin@1234")
        assert user is not None
        assert user.username == "globaladmin"
    except Exception as e:
        print(f"Authentication failed: {e}")
        raise
        
    # Test 2: Normal queries still block RLS without context
    # Note: In CI, the test database user (postgres/telite_ci) is a superuser. 
    # PostgreSQL always bypasses RLS for superusers, so we can only assert this
    # if the connection is running as a non-superuser (e.g. telite_app in local dev).
    is_superuser = db_session.execute(text("SELECT usesuper FROM pg_user WHERE usename = current_user")).scalar()
    
    if not is_superuser:
        repo = UserRepository(db_session)
        user2 = repo.get_by_username("globaladmin")
        assert user2 is None, "RLS failed to block normal query!"
    else:
        print("Skipping RLS block assertion because current database user is a superuser.")
