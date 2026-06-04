import sqlite3
import os

db_path = r"c:\Users\kamal\OneDrive\Desktop\telite-lms\telite-backend\data\telite_lms.db"

def delete_org(org_id: int):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    org = cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
    if not org:
        print(f"Organization {org_id} not found in SQLite db.")
        return
        
    print(f"Found org: {dict(org)}")
    
    users = cursor.execute("SELECT id FROM users WHERE org_id = ?", (org_id,)).fetchall()
    user_ids = [u["id"] for u in users]
    print(f"Deleting {len(user_ids)} users associated with org {org_id}...")
    
    for u_id in user_ids:
        cursor.execute("DELETE FROM users WHERE id = ?", (u_id,))
        
    cursor.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
    
    conn.commit()
    conn.close()
    print(f"Successfully deleted organization {org_id}.")

if __name__ == "__main__":
    delete_org(5)
