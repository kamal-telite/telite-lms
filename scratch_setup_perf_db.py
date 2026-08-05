import os
import sys
import uuid
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.models.user import User
from app.models.organization import Organization
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

PERF_DB_URL = "postgresql+psycopg://postgres:postgres123@localhost:55432/telite_perf_db"

def populate_perf_db():
    engine = create_engine(PERF_DB_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if org exists
        org = db.query(Organization).filter_by(id=1).first()
        if not org:
            print("Creating organization...")
            db.execute(text("""
                INSERT INTO organizations (id, name, slug, type, domain, status, plan, created_at, updated_at)
                VALUES (1, 'Perf Org', 'perf-org', 'b2b', 'perf.example.com', 'active', 'free', NOW(), NOW())
                ON CONFLICT (id) DO NOTHING;
            """))
            db.commit()
            
        # Count existing users
        existing_users = db.query(User).filter_by(org_id=1).count()
        target_users = 10000
        
        if existing_users >= target_users:
            print(f"Database already has {existing_users} users. Skipping generation.")
            return
            
        users_to_create = target_users - existing_users
        print(f"Generating {users_to_create} synthetic users in batches...")
        
        from datetime import datetime, timezone
        
        batch_size = 1000
        hashed_pw = get_password_hash("password123")
        now = datetime.now(timezone.utc)
        
        start_time = time.time()
        for i in range(0, users_to_create, batch_size):
            batch = []
            for j in range(min(batch_size, users_to_create - i)):
                idx = existing_users + i + j
                user_id = str(uuid.uuid4())
                batch.append({
                    "id": user_id,
                    "email": f"perfuser_{idx}@example.com",
                    "username": f"perfuser_{idx}",
                    "password_hash": hashed_pw,
                    "full_name": f"Perf User {idx}",
                    "is_active": True,
                    "is_platform_admin": False,
                    "status": "active",
                    "role": "learner",
                    "org_id": 1,
                    "created_at": now,
                    "theme_preference": "system",
                    "avatar_initials": "PU",
                    "gradient_start": "#000000",
                    "gradient_end": "#FFFFFF",
                    "pal_score": 0,
                    "pal_completion_pct": 0,
                    "pal_quiz_avg": 0,
                    "pal_time_spent_hours": 0,
                    "pal_task_completion_pct": 0,
                    "streak_days": 0,
                    "courses_completed": 0,
                    "total_courses": 0,
                    "course_progress_json": "[]"
                })
            
            # Bulk insert using raw SQL
            db.execute(
                text("""
                    INSERT INTO users (id, email, username, password_hash, full_name, is_active, is_platform_admin, status, role, org_id, created_at, theme_preference, avatar_initials, gradient_start, gradient_end, pal_score, pal_completion_pct, pal_quiz_avg, pal_time_spent_hours, pal_task_completion_pct, streak_days, courses_completed, total_courses, course_progress_json)
                    VALUES (:id, :email, :username, :password_hash, :full_name, :is_active, :is_platform_admin, :status, :role, :org_id, :created_at, :theme_preference, :avatar_initials, :gradient_start, :gradient_end, :pal_score, :pal_completion_pct, :pal_quiz_avg, :pal_time_spent_hours, :pal_task_completion_pct, :streak_days, :courses_completed, :total_courses, :course_progress_json)
                """),
                batch
            )
            db.commit()
            print(f"Inserted {i + len(batch)} / {users_to_create} users...")
            
        end_time = time.time()
        print(f"Finished generating {users_to_create} users in {end_time - start_time:.2f} seconds.")
        
    finally:
        db.close()

if __name__ == "__main__":
    populate_perf_db()
