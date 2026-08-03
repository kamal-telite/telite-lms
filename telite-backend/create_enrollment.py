"""
Create an enrollment request for testing
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

def create_enrollment():
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
            # Create an enrollment request for globaladmin to backend-development category
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            now_dt = datetime.now()
            result = conn.execute(text("""
                INSERT INTO enrollment_requests (id, full_name, email, category_slug, request_type, domain_verified, status, requested_at, reviewed_by, reviewed_at, org_id, created_at)
                VALUES ('test-enr-1', 'Global Admin', 'globaladmin@ktlearn.local', 'backend-development', 'manual', false, 'approved', :now_str, 'globaladmin', :now_str, 1, :now_dt)
                ON CONFLICT (id) DO UPDATE SET status = 'approved', reviewed_at = :now_str
            """), {"now_str": now_str, "now_dt": now_dt})
            conn.commit()
            print("Created enrollment request for globaladmin to backend-development category")
            
            # Verify it was created
            result = conn.execute(text("""
                SELECT * FROM enrollment_requests WHERE email = 'globaladmin@ktlearn.local'
            """))
            rows = result.fetchall()
            print(f"\nEnrollment requests for globaladmin:")
            for row in rows:
                print(f"  {row}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_enrollment()
