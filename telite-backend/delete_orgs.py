import sqlite3

try:
    conn = sqlite3.connect("data/telite_lms.db")
    
    # KT TELEMATIC
    org_kt = conn.execute("SELECT id FROM organizations WHERE name LIKE '%KT TELEMATIC%'").fetchone()
    if org_kt:
        org_id = org_kt[0]
        conn.execute("DELETE FROM users WHERE org_id = ? OR organization_id = ?", (org_id, org_id))
        conn.execute("DELETE FROM categories WHERE org_id = ? OR organization_id = ?", (org_id, org_id))
        conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        print(f"Deleted KT TELEMATIC (ID: {org_id}) from SQLite")
    else:
        print("KT TELEMATIC not found in SQLite")
        
    # THDC-IHET
    org_thdc = conn.execute("SELECT id FROM organizations WHERE name LIKE '%THDC-IHET%' OR id = 3").fetchone()
    if org_thdc:
        org_id = org_thdc[0]
        conn.execute("DELETE FROM users WHERE org_id = ? OR organization_id = ?", (org_id, org_id))
        conn.execute("DELETE FROM categories WHERE org_id = ? OR organization_id = ?", (org_id, org_id))
        conn.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        print(f"Deleted THDC-IHET (ID: {org_id}) from SQLite")
    else:
        print("THDC-IHET not found in SQLite")
        
    conn.commit()
    conn.close()
except Exception as e:
    print(f"SQLite error: {e}")
