import pytest
from sqlalchemy import text, select
from fastapi import HTTPException
from app.api.auth import authenticate_user
from app.db.engine import get_db_session
from app.repositories.user_repo import UserRepository
from app.models.user import User

def test_login_rls_bypass():
    with get_db_session() as db:
        try:
            user = authenticate_user(db, "globaladmin", "GlobalAdmin@1234")
            assert user is not None
            assert user.username == "globaladmin"
            print("Authentication successful!")
        except Exception as e:
            print(f"Authentication failed: {e}")
            raise
        
        # Test normal queries still block RLS
        repo = UserRepository(db)
        user2 = repo.get_by_username("globaladmin")
        assert user2 is None, "RLS failed to block normal query!"
        print("RLS is active for normal queries.")
        
if __name__ == "__main__":
    test_login_rls_bypass()
    print("ALL TESTS PASSED")
