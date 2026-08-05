import os
import sys
import time
import uuid
import psutil
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.workers.celery_app import celery_app
from app.services.notification_service import NotificationService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.notification import Notification

PERF_DB_URL = "postgresql+psycopg://postgres:postgres123@localhost:55432/telite_perf_db"
engine = create_engine(PERF_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup environment for the test
os.environ["TELITE_DATABASE_URL"] = "postgresql+psycopg://postgres:postgres123@localhost:55432/telite_perf_db"

def clear_notifications():
    db = SessionLocal()
    try:
        db.execute(Notification.__table__.delete())
        db.commit()
    finally:
        db.close()

def run_benchmark():
    print("Starting Performance Benchmark...")
    clear_notifications()
    
    # We will test batch sizes
    batch_sizes = [1, 10, 100, 1000, 10000]
    results = []
    
    for size in batch_sizes:
        print(f"\n--- Testing Batch Size: {size} ---")
        
        # We need a user cohort or list. We'll use role='learner' since all 10,000 users are learners.
        # But wait, how do we target exactly 'size' users?
        # We can pass an explicit list of 'size' user IDs to the service!
        from sqlalchemy import text
        db = SessionLocal()
        users = db.execute(text("SELECT id FROM users LIMIT :limit"), {"limit": size}).fetchall()
        user_ids = [u[0] for u in users]
        db.close()
        
        target_entity_id = str(uuid.uuid4())
        
        # Measure API emit latency
        api_start = time.time()
        
        # We don't want to use standard emit_event because it might enqueue to the default queue.
        # Let's bypass emit_event and manually trigger the task, simulating emit_event
        # NotificationService.emit_event(
        #     db=db,
        #     event_name="announcement_created",
        #     actor_id=user_ids[0],
        #     target_entity_id=target_entity_id,
        #     target_entity_type="announcement",
        #     org_id=1,
        #     audience={"user_ids": user_ids},
        #     metadata={"title": f"Test {size}", "message": "Performance test"}
        # )
        
        context = {
            "title": f"Test {size}",
            "message": "Performance test",
            "announcement_id": target_entity_id,
            "course_title": "Perf Course",
            "course_id": "perf-course"
        }
        audience_dict = {"type": "org_all"}
        
        # Set exactly `size` users to is_active=True, rest to False
        db = SessionLocal()
        db.execute(text("UPDATE users SET is_active = false"))
        db.execute(text("UPDATE users SET is_active = true WHERE id IN (SELECT id FROM users LIMIT :limit)"), {"limit": size})
        db.commit()
        db.close()
        
        # Measure fan-out execution
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        
        from app.workers.notification_tasks import dispatch_fanout_task
        
        fanout_start = time.time()
        # Since it's a Celery task bound to self, we can use .apply() to run it synchronously locally
        result = dispatch_fanout_task.apply(kwargs={
            "event_name": "announcement.published",
            "org_id": 1,
            "context": context,
            "audience": audience_dict
        })
        fanout_time = time.time() - fanout_start
        
        mem_after = process.memory_info().rss
        mem_used_mb = (mem_after - mem_before) / (1024 * 1024)
        
        throughput = size / fanout_time if fanout_time > 0 else 0
        
        api_latency = time.time() - api_start
        print(f"Fan-out Completion Time: {fanout_time:.3f} seconds")
        print(f"API + Fan-out Total Latency: {api_latency*1000:.2f} ms")
        print(f"Throughput: {throughput:.2f} notifications/second")
        print(f"Worker Memory Delta: {mem_used_mb:.2f} MB")
        
        # Verify DB insertions
        db = SessionLocal()
        inserted_count = db.execute(text("SELECT COUNT(*) FROM notifications WHERE source_id = :tid"), {"tid": target_entity_id}).scalar()
        db.close()
        print(f"Notifications Persisted: {inserted_count} / {size}")
        
        if result.failed():
            print(f"Error in fan-out task: {result.traceback}")
            
        results.append({
            "size": size,
            "api_latency_ms": api_latency * 1000,
            "fanout_time_s": fanout_time,
            "throughput_nps": throughput,
            "mem_delta_mb": mem_used_mb,
            "success": inserted_count == size
        })
        
    print("\n--- Benchmark Summary ---")
    print(f"{'Size':<10} | {'API Lat (ms)':<15} | {'Fan-out (s)':<15} | {'Throughput (N/s)':<20} | {'Mem Delta (MB)':<15}")
    print("-" * 80)
    for r in results:
        print(f"{r['size']:<10} | {r['api_latency_ms']:<15.2f} | {r['fanout_time_s']:<15.3f} | {r['throughput_nps']:<20.2f} | {r['mem_delta_mb']:<15.2f}")

if __name__ == "__main__":
    run_benchmark()
