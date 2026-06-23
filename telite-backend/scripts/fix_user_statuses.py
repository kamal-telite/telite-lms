import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

STATUS_MAPPING = {
    "invited": "disabled",
    "pending_approval": "disabled",
    "approved": "disabled",
    "email_verified": "disabled",
    "rejected": "disabled",
}

def fix_statuses():
    db_url = os.getenv("TELITE_DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/telite_backend")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # Get before counts
        before_query = text("SELECT status, COUNT(*) FROM users GROUP BY status;")
        before_counts = session.execute(before_query).fetchall()
        
        affected_rows = 0
        
        for old_status, new_status in STATUS_MAPPING.items():
            update_query = text("""
                UPDATE users 
                SET status = :new_status 
                WHERE status = :old_status
            """)
            result = session.execute(update_query, {"new_status": new_status, "old_status": old_status})
            affected_rows += result.rowcount
            
        session.commit()
        
        # Get after counts
        after_counts = session.execute(before_query).fetchall()
        
        os.makedirs("Project_docs", exist_ok=True)
        with open("Project_docs/user_status_cleanup_report.md", "w") as f:
            f.write("# User Status Cleanup Report\n\n")
            f.write("## Before\n")
            for status, count in before_counts:
                f.write(f"- `{status}`: {count}\n")
                
            f.write(f"\n## Affected Rows\nTotal updated: {affected_rows}\n\n")
            
            f.write("## After\n")
            for status, count in after_counts:
                f.write(f"- `{status}`: {count}\n")
                
        print(f"Cleanup complete. Updated {affected_rows} rows.")

if __name__ == "__main__":
    fix_statuses()
