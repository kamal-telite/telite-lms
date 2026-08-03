"""Integration tests for eager assignment Celery workers."""

import os
os.environ["TELITE_TEST_DATABASE_URL"] = "sqlite:///test_workers.db"
os.environ["TELITE_DATABASE_URL"] = "sqlite:///test_workers.db"

import pytest
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.task import Task
from app.models.task_workflow import TaskAssignment
from app.workers.task_assignment_tasks import generate_bulk_assignments, generate_enrollment_assignments

@pytest.fixture
def sqlite_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    # Mock get_db_session to return our sqlite session
    class DummyContextManager:
        def __enter__(self): return session
        def __exit__(self, *args): pass
    
    monkeypatch.setattr("app.db.engine.get_db_session", lambda: DummyContextManager())
    
    yield session
    session.close()

@pytest.fixture
def setup_org_and_users(sqlite_session):
    from app.models.organization import Organization
    from app.models.user import User
    
    org = Organization(id=1, name='Test Org', slug='testorg', type='company', domain='test.com', status='active', plan='free')
    sqlite_session.add(org)
    
    for i in range(1, 4):
        user = User(
            id=f'learner-{i}', 
            username=f'learner{i}',
            email=f'learner{i}@test.com', 
            full_name=f'Learner {i}', 
            password_hash='hash', 
            role='learner', 
            org_id=1, 
            is_active=True,
            avatar_initials='L',
            gradient_start='#000',
            gradient_end='#111'
        )
        sqlite_session.add(user)
    
    sqlite_session.commit()

@pytest.fixture
def global_task(sqlite_session, setup_org_and_users):
    task = Task(
        id="task-global-1",
        title="Global Task",
        assigned_label="All Learners",
        assignment_scope="all",
        category_slug="kt-foundations",
        status="pending",
        org_id=1,
        assignment_generation_status="pending",
    )
    sqlite_session.add(task)
    sqlite_session.commit()
    return task

def test_generate_bulk_assignments_success_and_idempotency(sqlite_session, global_task):
    # First execution should create 3 assignments
    res = generate_bulk_assignments.apply(args=(global_task.id, 1)).result
    assert res["status"] == "completed"
    assert res["created"] == 3
    
    # Verify DB
    assignments = sqlite_session.query(TaskAssignment).where(TaskAssignment.task_id == global_task.id).all()
    assert len(assignments) == 3
    
    # Second execution should create 0 assignments (idempotency via ON CONFLICT DO NOTHING)
    res2 = generate_bulk_assignments.apply(args=(global_task.id, 1)).result
    assert res2["status"] == "completed"
    assert res2["created"] == 0
    
    assignments2 = sqlite_session.query(TaskAssignment).where(TaskAssignment.task_id == global_task.id).all()
    assert len(assignments2) == 3

def test_generate_enrollment_assignments_catches_all_global_tasks(sqlite_session, global_task):
    # Set the global task to "in_progress" (simulating a race condition where bulk generation is running)
    global_task.assignment_generation_status = "in_progress"
    sqlite_session.commit()
    
    # Run the enrollment assignment worker for a new learner
    from app.models.user import User
    new_user = User(
        id='learner-new', 
        username='learnernew',
        email='new@test.com', 
        full_name='Learner New', 
        password_hash='hash', 
        role='learner', 
        org_id=1, 
        is_active=True,
        avatar_initials='LN',
        gradient_start='#000',
        gradient_end='#111'
    )
    sqlite_session.add(new_user)
    sqlite_session.commit()
    
    res = generate_enrollment_assignments.apply(args=('learner-new', 1)).result
    assert res["status"] == "completed"
    assert res["created"] == 1
    
    assignment = sqlite_session.query(TaskAssignment).where(
        TaskAssignment.task_id == global_task.id, 
        TaskAssignment.learner_id == 'learner-new'
    ).first()
    assert assignment is not None

def test_worker_retry_after_failure(sqlite_session, setup_org_and_users, monkeypatch):
    from app.models.task import Task
    
    # Create a fresh task for this test to ensure it attempts to create assignments
    test_task = Task(
        id='task-retry-1', 
        org_id=1, 
        title='Retry Task', 
        assignment_scope='all', 
        assignment_generation_status='pending',
        status='published',
        assigned_label='Global Task',
        category_slug='general'
    )
    sqlite_session.add(test_task)
    sqlite_session.commit()

    import sqlalchemy.orm.session
    original_commit = sqlalchemy.orm.session.Session.commit
    
    commit_failed = False
    def mock_commit(self, *args, **kwargs):
        nonlocal commit_failed
        if not commit_failed:
            commit_failed = True
            raise Exception("DB Connection Lost")
        return original_commit(self, *args, **kwargs)
        
    monkeypatch.setattr("sqlalchemy.orm.session.Session.commit", mock_commit)
    
    def mock_retry(*args, **kwargs):
        raise Exception("Retry Triggered")
        
    monkeypatch.setattr("celery.app.task.Task.retry", mock_retry)
    
    with pytest.raises(Exception, match="Retry Triggered"):
        generate_bulk_assignments.apply(args=(test_task.id, 1), throw=True)
        
    sqlite_session.refresh(test_task)
    assert test_task.assignment_generation_status == "failed"
    assert "DB Connection Lost" in test_task.generation_error
