"""
Create proper enrollment for learner to test the course
"""
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import create_engine, text
from datetime import datetime

def create_learner_enrollment():
    # Get database URL from environment
    db_url = os.getenv("TELITE_DATABASE_URL", "")
    if not db_url:
        # Build from individual components
        host = os.getenv("TELITE_POSTGRES_HOST") or os.getenv("POSTGRES_HOST") or "localhost"
        port = os.getenv("TELITE_POSTGRES_PORT") or os.getenv("POSTGRES_PORT") or "5432"
        db = os.getenv("TELITE_POSTGRES_DB") or os.getenv("POSTGRES_DB")
        user = os.getenv("TELITE_POSTGRES_USER") or os.getenv("POSTGRES_USER")
        pw = os.getenv("TELITE_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
        
        if not all([db, user, pw]):
            print("Missing database credentials")
            return
        
        from urllib.parse import quote_plus
        db_url = f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(pw)}@{host}:{port}/{db}"
    
    print(f"Database URL: {db_url}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # First check what category the course-python course belongs to
            result = conn.execute(text("""
                SELECT id, name, category_slug FROM courses WHERE id = 'course-python'
            """))
            course = result.fetchone()
            if course:
                print(f"Course found: {course[1]}, category: {course[2]}")
                category_slug = course[2]
            else:
                print("Course not found")
                return
            
            # Check if learner has enrollment request for this category
            result = conn.execute(text("""
                SELECT * FROM enrollment_requests 
                WHERE email = 'learner1@ktlearn.local' 
                AND category_slug = :category_slug
            """), {"category_slug": category_slug})
            existing = result.fetchone()
            
            if existing:
                print(f"Existing enrollment request found: {existing}")
                # Update it to approved if needed
                if existing[7] != 'approved':  # status column
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    conn.execute(text("""
                        UPDATE enrollment_requests 
                        SET status = 'approved', reviewed_at = :now, reviewed_by = 'system'
                        WHERE id = :id
                    """), {"now": now_str, "id": existing[0]})
                    conn.commit()
                    print("Updated enrollment request to approved")
            else:
                # Create new enrollment request
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                now_dt = datetime.now()
                result = conn.execute(text("""
                    INSERT INTO enrollment_requests (id, full_name, email, category_slug, request_type, domain_verified, status, requested_at, reviewed_by, reviewed_at, org_id, created_at)
                    VALUES ('enr-learner1-python', 'KT Learner 1', 'learner1@ktlearn.local', :category_slug, 'manual', false, 'approved', :now_str, 'system', :now_str, 1, :now_dt)
                """), {"category_slug": category_slug, "now_str": now_str, "now_dt": now_dt})
                conn.commit()
                print("Created new enrollment request")
            
            # Verify the enrollment
            result = conn.execute(text("""
                SELECT * FROM enrollment_requests 
                WHERE email = 'learner1@ktlearn.local' 
                AND category_slug = :category_slug
            """), {"category_slug": category_slug})
            final = result.fetchone()
            print(f"Final enrollment status: {final}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_learner_enrollment()
