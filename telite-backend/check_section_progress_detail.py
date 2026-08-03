"""
Check detailed section progress with course information
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

def check_section_progress_detail():
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
            # Get section progress with course section info
            result = conn.execute(text("""
                SELECT sp.id, sp.user_id, sp.section_id, sp.status, sp.time_spent_seconds, 
                       cs.title as section_title, cs.minimum_time_seconds, cs.course_id
                FROM section_progress sp
                JOIN course_sections cs ON sp.section_id = cs.id
                WHERE sp.user_id = 'kt_learner_1'
                ORDER BY sp.section_id
                LIMIT 10
            """))
            rows = result.fetchall()
            print(f"\nSection progress for kt_learner_1:")
            for row in rows:
                print(f"  Section: {row[5]} (ID: {row[2]})")
                print(f"    Status: {row[3]}")
                print(f"    Time spent: {row[4]}s")
                print(f"    Minimum required: {row[6]}s")
                print(f"    Course: {row[7]}")
                print(f"    Time met: {row[4] >= row[6] if row[6] else 'N/A'}")
                print()
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_section_progress_detail()
