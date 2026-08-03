"""
Check progression_rules table structure and data
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

def check_progression_rules():
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
            # Check structure
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'progression_rules' 
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            print(f"\nProgression rules table structure:")
            for column in columns:
                print(f"  {column[0]}: {column[1]}")
                
            # Get sample data
            print(f"\nSample data:")
            result = conn.execute(text("SELECT * FROM progression_rules LIMIT 10"))
            rows = result.fetchall()
            for row in rows:
                print(f"  {row}")
                
            # Count total rules
            result = conn.execute(text("SELECT COUNT(*) FROM progression_rules"))
            count = result.fetchone()[0]
            print(f"\nTotal progression rules: {count}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_progression_rules()
