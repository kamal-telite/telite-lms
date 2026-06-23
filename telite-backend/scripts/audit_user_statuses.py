import os
import csv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def run_audit():
    # Use the local SQLite test DB if the Postgres one fails or isn't set up
    db_url = os.getenv("TELITE_DATABASE_URL", "sqlite:///test_telite.db")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as session:
        # 1. Status Distribution
        dist_query = text("SELECT status, COUNT(*) FROM users GROUP BY status ORDER BY count DESC;")
        dist_results = session.execute(dist_query).fetchall()
        
        # 2. Anomalous rows
        anom_query = text("""
            SELECT id, email, username, org_id, status, created_at 
            FROM users 
            WHERE status NOT IN ('active', 'suspended', 'disabled');
        """)
        anom_results = session.execute(anom_query).fetchall()
        
        # 3. Impact Analysis stats
        impact_query = text("""
            SELECT status, COUNT(*), MIN(created_at) as min_date, MAX(created_at) as max_date
            FROM users
            WHERE status NOT IN ('active', 'suspended', 'disabled')
            GROUP BY status;
        """)
        impact_results = session.execute(impact_query).fetchall()

        # 4. Duplicate Username Check
        dup_query = text("""
            SELECT username, COUNT(*)
            FROM users
            GROUP BY username
            HAVING COUNT(*) > 1;
        """)
        dup_results = session.execute(dup_query).fetchall()
        
        os.makedirs("Project_docs", exist_ok=True)
        
        # Write CSV
        with open("Project_docs/user_status_audit.csv", "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "email", "username", "org_id", "status", "created_at"])
            for row in anom_results:
                writer.writerow([row.id, row.email, row.username, row.org_id, row.status, row.created_at])
                
        # Write MD
        with open("Project_docs/user_status_audit.md", "w") as f:
            f.write("# User Status Audit Report\n\n")
            
            f.write("## 1. Status Distribution\n")
            f.write("| Status | Count |\n|---|---|\n")
            for row in dist_results:
                f.write(f"| {row[0]} | {row[1]} |\n")
                
            f.write("\n## 2. Impact Analysis (Anomalous Records)\n")
            f.write("| Status | Count | Oldest Record | Newest Record |\n|---|---|---|---|\n")
            for row in impact_results:
                f.write(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |\n")
                
            f.write("\n## 3. Duplicate Username Report\n")
            if dup_results:
                f.write("| Username | Count |\n|---|---|\n")
                for row in dup_results:
                    f.write(f"| {row[0]} | {row[1]} |\n")
            else:
                f.write("No duplicate usernames found.\n")
                
        print(f"Audit complete. Found {len(anom_results)} anomalous records.")

if __name__ == "__main__":
    run_audit()
