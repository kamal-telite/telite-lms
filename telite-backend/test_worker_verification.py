import os
import pytest
from datetime import datetime, timezone, timedelta

# Set up environment
os.environ["TELITE_DB_BACKEND"] = "postgres"
os.environ["TELITE_DATABASE_URL"] = "postgresql+psycopg://postgres:postgres123@localhost:5432/test_telite_backend"
os.environ["REDIS_ENABLED"] = "false"
os.environ["SMTP_USER"] = "" # Force email failure for dead letter test

from app.db import engine
from app.models import Organization, User, EnrollmentRequest, Course, Notification
from app.workers.reminder_tasks import enrollment_reminders
from app.workers.notification_tasks import send_email_notification
from app.workers.reconciliation import reconcile_all_orgs
from sqlalchemy import text

@pytest.fixture(scope="module", autouse=True)
def setup_teardown_db():
    eng = engine.get_engine()
    # To avoid the drop_all postgres bug, we will just clear the tables manually
    with eng.connect() as conn:
        conn.execute(text("TRUNCATE TABLE audit_log CASCADE"))
        conn.execute(text("TRUNCATE TABLE notifications CASCADE"))
        conn.execute(text("TRUNCATE TABLE enrollment_requests CASCADE"))
        conn.execute(text("TRUNCATE TABLE users CASCADE"))
        conn.execute(text("TRUNCATE TABLE organizations CASCADE"))
        # Seed system org (id=0) for platform audit logs
        conn.execute(text(
            "INSERT INTO organizations (id, name, type, domain, status, plan) "
            "VALUES (0, 'System', 'system', 'system.local', 'active', 'enterprise')"
        ))
        conn.commit()
    yield

def test_tenant_isolation_enrollment_reminders():
    from app.db.engine import get_platform_session, get_tenant_session
    
    with get_platform_session() as session:
        # Create Org A
        org_a = Organization(name="Org A", type="company", domain="a.com", status="active", plan="pro")
        # Create Org B
        org_b = Organization(name="Org B", type="company", domain="b.com", status="active", plan="pro")
        session.add_all([org_a, org_b])
        session.commit()
        org_a_id = org_a.id
        org_b_id = org_b.id

    with get_tenant_session(org_a_id) as session:
        admin_a = User(id="admin-a", org_id=org_a_id, email="admin@a.com", username="admin_a", full_name="Admin A", role="admin", password_hash="hash", avatar_initials="AA", gradient_start="#000", gradient_end="#000")
        req_a = EnrollmentRequest(id="req-a", org_id=org_a_id, email="u@a.com", full_name="U A", category_slug="c-1", request_type="enroll", status="pending", requested_at="now")
        req_a.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        session.add_all([admin_a, req_a])
        session.commit()

    with get_tenant_session(org_b_id) as session:
        admin_b = User(id="admin-b", org_id=org_b_id, email="admin@b.com", username="admin_b", full_name="Admin B", role="admin", password_hash="hash", avatar_initials="BB", gradient_start="#000", gradient_end="#000")
        req_b = EnrollmentRequest(id="req-b", org_id=org_b_id, email="u@b.com", full_name="U B", category_slug="c-2", request_type="enroll", status="pending", requested_at="now")
        req_b.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        session.add_all([admin_b, req_b])
        session.commit()

    # Run the worker manually (synchronously for the test)
    # This task loops through both orgs and calls send_email_notification.delay
    # In tests without a celery worker running, .delay might just queue it or fail.
    # To test tenant isolation, we can run it synchronously. But wait, .delay uses Celery. 
    # Let's mock send_email_notification.delay
    called_args = []
    
    # Monkeypatch the delay
    original_delay = send_email_notification.delay
    def mock_delay(**kwargs):
        called_args.append(kwargs)
    send_email_notification.delay = mock_delay
    
    try:
        res = enrollment_reminders()
        assert res["orgs_processed"] >= 2
        assert res["reminders_sent"] == 2
        
        # Verify Org A only sent to Admin A
        org_a_calls = [c for c in called_args if c["org_id"] == org_a_id]
        assert len(org_a_calls) == 1
        assert org_a_calls[0]["to_email"] == "admin@a.com"
        
        # Verify Org B only sent to Admin B
        org_b_calls = [c for c in called_args if c["org_id"] == org_b_id]
        assert len(org_b_calls) == 1
        assert org_b_calls[0]["to_email"] == "admin@b.com"
    finally:
        send_email_notification.delay = original_delay


def test_audit_logs_and_reconciliation_metrics():
    # Run reconciliation worker synchronously
    res = reconcile_all_orgs()
    assert res["status"] == "completed"
    
    # Verify metrics stored in Audit Log
    from app.db.engine import get_platform_session
    with get_platform_session() as session:
        audits = session.execute(text("SELECT action, metadata_json FROM audit_log WHERE action = 'worker.reconciliation.completed'")).fetchall()
        assert len(audits) > 0
        latest = audits[-1]
        import json
        meta = json.loads(latest.metadata_json)
        assert "organizations_processed" in meta
        assert "users_reconciled" in meta


def test_dead_letter_queue():
    from app.db.engine import get_platform_session
    from celery.exceptions import Retry
    
    # Clean audit logs and insert org 1
    with get_platform_session() as session:
        session.execute(text("TRUNCATE TABLE audit_log CASCADE"))
        session.execute(text("INSERT INTO organizations (id, name, type, domain, status, plan) VALUES (1, 'Org 1', 'company', 'org1.com', 'active', 'free') ON CONFLICT DO NOTHING"))
        session.commit()

    # The send_email_notification task has max_retries=3.
    # We will simulate calling it with retry_count 0, 1, 2, and 3.
    from unittest.mock import patch, PropertyMock
    
    with patch("celery.app.task.Context.retries", new_callable=PropertyMock) as mock_retries:
        # Retry 1
        mock_retries.return_value = 0
        try:
            send_email_notification(to_email="bad@b.com", name="Bad", title="Test", body="Test", org_id=1, notif_type="info")
        except Exception:
            pass
            
        # Dead Letter (retries reached max 3)
        mock_retries.return_value = 3
        try:
            send_email_notification(to_email="bad@b.com", name="Bad", title="Test", body="Test", org_id=1, notif_type="info")
        except Exception:
            pass

    with get_platform_session() as session:
        audits = session.execute(text("SELECT action, target_id, result FROM audit_log ORDER BY created_at ASC")).fetchall()
        actions = [a.action for a in audits]
        assert "notification.retry" in actions
        assert "notification.dead_letter" in actions
        
        dead_letters = [a for a in audits if a.action == "notification.dead_letter"]
        assert len(dead_letters) == 1
        assert dead_letters[0].result == "failed"
        assert dead_letters[0].target_id == "bad@b.com"
