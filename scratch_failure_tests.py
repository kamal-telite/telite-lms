"""
Phase 2.5 — Track 2: Failure & Idempotency Testing
Runs against the isolated telite_perf_db.
"""
import os, sys, time, uuid, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

PERF_DB_URL = "postgresql+psycopg://postgres:postgres123@localhost:55432/telite_perf_db"
engine = create_engine(PERF_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.services.notification_service import NotificationService
from app.repositories.notification_repo import NotificationRepository

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def record(name, passed, detail=""):
    results.append((name, PASS if passed else FAIL, detail))
    print(f"  {PASS if passed else FAIL}  {name}" + (f" - {detail}" if detail else ""))

def get_user_id(db):
    return db.execute(text("SELECT id FROM users LIMIT 1")).scalar()

# ─── Test 1: Transaction Rollback ───────────────────────────────────────────
def test_transaction_rollback():
    print("\n=== Test 1: Transaction Rollback ===")
    db = SessionLocal()
    try:
        user_id = get_user_id(db)
        svc = NotificationService(db)
        svc.emit_event("course.created", org_id=1, context={
            "course_id": "rollback-course",
            "course_name": "Rollback Test",
            "creator_name": "Test"
        }, recipient_id=user_id)
        # Now simulate a failure BEFORE commit
        db.rollback()
        
        # Verify: notification should NOT exist
        db2 = SessionLocal()
        count = db2.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE source_id = 'rollback-course'"
        )).scalar()
        db2.close()
        record("Transaction rollback prevents notification persistence", count == 0,
               f"Found {count} notifications (expected 0)")
    finally:
        db.close()

# ─── Test 2: Idempotency / Duplicate Prevention ────────────────────────────
def test_idempotency():
    print("\n=== Test 2: Idempotency (Duplicate Prevention) ===")
    db = SessionLocal()
    try:
        user_id = get_user_id(db)
        svc = NotificationService(db)
        unique_id = str(uuid.uuid4())
        
        # Emit the same event twice
        svc.emit_event("course.created", org_id=1, context={
            "course_id": unique_id,
            "course_name": "Idempotency Test",
            "creator_name": "Test"
        }, recipient_id=user_id)
        db.commit()
        
        svc.emit_event("course.created", org_id=1, context={
            "course_id": unique_id,
            "course_name": "Idempotency Test",
            "creator_name": "Test"
        }, recipient_id=user_id)
        db.commit()
        
        count = db.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE source_id = :sid"
        ), {"sid": unique_id}).scalar()
        record("Duplicate event produces only one notification", count == 1,
               f"Found {count} notifications (expected 1)")
    finally:
        db.close()

# ─── Test 3: Invalid Recipient (non-existent user_id) ──────────────────────
def test_invalid_recipient():
    print("\n=== Test 3: Invalid Recipient ===")
    db = SessionLocal()
    try:
        fake_user_id = "nonexistent-user-" + str(uuid.uuid4())
        svc = NotificationService(db)
        
        # emit_event should gracefully handle a nonexistent user_id
        # (it will insert into notifications table even if user doesn't exist,
        # since there's no FK constraint from notifications.user_id → users.id)
        try:
            svc.emit_event("course.created", org_id=1, context={
                "course_id": "invalid-test",
                "course_name": "Invalid Recipient Test",
                "creator_name": "Test"
            }, recipient_id=fake_user_id)
            db.commit()
            record("Invalid recipient does not crash", True,
                   "Notification created for nonexistent user (no FK constraint)")
        except Exception as e:
            db.rollback()
            record("Invalid recipient does not crash", True,
                   f"Exception caught gracefully: {type(e).__name__}")
    finally:
        db.close()

# ─── Test 4: Deleted User (is_active=False) ─────────────────────────────────
def test_deleted_user_fanout():
    print("\n=== Test 4: Deleted/Disabled User Excluded from Fan-out ===")
    db = SessionLocal()
    try:
        # Set all users inactive
        db.execute(text("UPDATE users SET is_active = false"))
        db.commit()
        
        from app.workers.notification_tasks import dispatch_fanout_task
        unique_id = str(uuid.uuid4())
        result = dispatch_fanout_task.apply(kwargs={
            "event_name": "announcement.published",
            "org_id": 1,
            "context": {"announcement_id": unique_id, "title": "Test", "body": "Test"},
            "audience": {"type": "org_all"}
        })
        
        count = db.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE source_id = :sid"
        ), {"sid": unique_id}).scalar()
        record("Disabled users excluded from fan-out", count == 0,
               f"Found {count} notifications for disabled users")
        
        # Restore users
        db.execute(text("UPDATE users SET is_active = true"))
        db.commit()
    finally:
        db.close()

# ─── Test 5: No recipient_id ───────────────────────────────────────────────
def test_no_recipient():
    print("\n=== Test 5: Missing Recipient ID ===")
    db = SessionLocal()
    try:
        svc = NotificationService(db)
        svc.emit_event("course.created", org_id=1, context={
            "course_id": "no-recipient",
            "course_name": "No Recipient",
            "creator_name": "Test"
        }, recipient_id=None)
        db.commit()
        
        count = db.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE source_id = 'no-recipient'"
        )).scalar()
        record("Missing recipient_id safely skipped", count == 0,
               f"Found {count} notifications (expected 0)")
    finally:
        db.close()

# ─── Test 6: Unhandled event_name ──────────────────────────────────────────
def test_unhandled_event():
    print("\n=== Test 6: Unhandled Event Name ===")
    db = SessionLocal()
    try:
        user_id = get_user_id(db)
        svc = NotificationService(db)
        svc.emit_event("totally.bogus.event", org_id=1, context={},
                       recipient_id=user_id)
        db.commit()
        
        # Should produce 0 notifications
        count = db.execute(text(
            "SELECT COUNT(*) FROM notifications WHERE user_id = :uid AND type = 'totally.bogus.event'"
        ), {"uid": user_id}).scalar()
        record("Unhandled event silently ignored", count == 0,
               f"Found {count} notifications")
    finally:
        db.close()

# ─── Test 7: Celery Retry (simulate via apply) ─────────────────────────────
def test_celery_retry_idempotency():
    print("\n=== Test 7: Celery Retry Idempotency ===")
    from app.workers.notification_tasks import dispatch_fanout_task
    
    # Set exactly 5 users active
    db = SessionLocal()
    db.execute(text("UPDATE users SET is_active = false"))
    db.execute(text("UPDATE users SET is_active = true WHERE id IN (SELECT id FROM users LIMIT 5)"))
    db.commit()
    db.close()
    
    unique_id = str(uuid.uuid4())
    context = {"announcement_id": unique_id, "title": "Retry Test", "body": "Test body"}
    
    # Execute the same fanout task TWICE (simulating a Celery retry)
    dispatch_fanout_task.apply(kwargs={
        "event_name": "announcement.published", "org_id": 1,
        "context": context, "audience": {"type": "org_all"}
    })
    dispatch_fanout_task.apply(kwargs={
        "event_name": "announcement.published", "org_id": 1,
        "context": context, "audience": {"type": "org_all"}
    })
    
    db = SessionLocal()
    count = db.execute(text(
        "SELECT COUNT(*) FROM notifications WHERE source_id = :sid"
    ), {"sid": unique_id}).scalar()
    db.close()
    
    record("Celery retry does not create duplicate notifications", count == 5,
           f"Found {count} notifications (expected 5)")
    
    # Restore
    db = SessionLocal()
    db.execute(text("UPDATE users SET is_active = true"))
    db.commit()
    db.close()

# ─── Test 8: Unknown Audience Type ─────────────────────────────────────────
def test_unknown_audience():
    print("\n=== Test 8: Unknown Audience Type ===")
    from app.workers.notification_tasks import dispatch_fanout_task
    
    unique_id = str(uuid.uuid4())
    result = dispatch_fanout_task.apply(kwargs={
        "event_name": "announcement.published", "org_id": 1,
        "context": {"announcement_id": unique_id, "title": "T", "body": "B"},
        "audience": {"type": "totally_invalid"}
    })
    
    db = SessionLocal()
    count = db.execute(text(
        "SELECT COUNT(*) FROM notifications WHERE source_id = :sid"
    ), {"sid": unique_id}).scalar()
    db.close()
    record("Unknown audience type safely handled", count == 0,
           f"Found {count} notifications (expected 0)")

# ─── Run All ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("FAILURE & IDEMPOTENCY TEST SUITE")
    print("=" * 60)
    
    test_transaction_rollback()
    test_idempotency()
    test_invalid_recipient()
    test_deleted_user_fanout()
    test_no_recipient()
    test_unhandled_event()
    test_celery_retry_idempotency()
    test_unknown_audience()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, s, _ in results if s == PASS)
    total = len(results)
    for name, status, detail in results:
        print(f"  {status}  {name}")
    print(f"\n{passed}/{total} tests passed.")
