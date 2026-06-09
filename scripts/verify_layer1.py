import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../telite-backend/.env'))

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../telite-backend')))

from app.db.engine import get_engine
from sqlalchemy import text

def verify_db():
    engine = get_engine()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar()
        db = conn.execute(text("SELECT current_database();")).scalar()
        user = conn.execute(text("SELECT current_user;")).scalar()
        
        print("\n--- Layer 1: Runtime Database Verification ---")
        print(f"Version: {version}")
        print(f"Current Database: {db}")
        print(f"Current User: {user}")
        print("----------------------------------------------\n")

if __name__ == "__main__":
    verify_db()
