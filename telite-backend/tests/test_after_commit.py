import pytest
from app.models.organization import Organization

def test_after_commit_callback_execution(db_session):
    executed = []
    
    def my_callback():
        executed.append(True)
    
    db_session.info.setdefault("after_commit_callbacks", []).append(my_callback)
    
    # Do some DB work to trigger a real commit
    org = Organization(name="Test Org DB Commit", slug="test-org-db-commit", status="active", plan="enterprise", type="b2b", domain="test-org-db-commit.com")
    db_session.add(org)
    db_session.commit()
    
    assert len(executed) == 1
    assert "after_commit_callbacks" not in db_session.info or not db_session.info["after_commit_callbacks"]

def test_after_commit_callback_rollback(db_session):
    executed = []
    
    def my_callback():
        executed.append(True)
    
    db_session.info.setdefault("after_commit_callbacks", []).append(my_callback)
    
    org = Organization(name="Test Org DB Rollback", slug="test-org-db-rollback", status="active", plan="enterprise", type="b2b", domain="test-org-db-rollback.com")
    db_session.add(org)
    db_session.rollback()
    
    assert len(executed) == 0
    assert "after_commit_callbacks" not in db_session.info or not db_session.info["after_commit_callbacks"]

def test_after_commit_callback_multiple(db_session):
    executed = []
    
    def cb1(): executed.append(1)
    def cb2(): executed.append(2)
    def cb_fail(): raise ValueError("Intentional failure")
    def cb3(): executed.append(3)
    
    db_session.info.setdefault("after_commit_callbacks", []).extend([cb1, cb2, cb_fail, cb3])
    
    org = Organization(name="Test Org DB Multi", slug="test-org-db-multi", status="active", plan="enterprise", type="b2b", domain="test-org-db-multi.com")
    db_session.add(org)
    db_session.commit()
    
    # Even if one fails, others should execute if implemented correctly
    # Note: Currently our implementation loops over them, and if one raises an exception, we catch it and continue!
    # Let's verify that.
    assert executed == [1, 2, 3]
    assert "after_commit_callbacks" not in db_session.info or not db_session.info["after_commit_callbacks"]
