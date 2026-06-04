import sys
import os
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

from app.services.store import get_conn

def delete_org(org_id: int):
    with get_conn() as conn:
        print(f"Deleting organization {org_id}...")
        
        # Check if org exists
        org = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
        if not org:
            print(f"Organization {org_id} not found.")
            return

        print(f"Found org: {dict(org)}")
        
        # Delete related users
        users = conn.execute("SELECT id FROM users WHERE org_id = ?", (org_id,)).fetchall()
        user_ids = [u["id"] for u in users]
        print(f"Deleting {len(user_ids)} users associated with org {org_id}...")
        
        for u_id in user_ids:
            conn.execute("DELETE FROM users WHERE id = ?", (u_id,))
            
        # Delete the org
        conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        
        conn.commit()
        print(f"Successfully deleted organization {org_id}.")

if __name__ == "__main__":
    delete_org(5)
