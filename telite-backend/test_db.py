import sqlite3

conn = sqlite3.connect("data/telite_lms.db")
conn.row_factory = sqlite3.Row

print("--- USERS ---")
for row in conn.execute("SELECT id, email, role, is_platform_admin, org_id, organization_id FROM users WHERE email LIKE '%kamal%'"):
    print(dict(row))

print("\n--- ORGANIZATIONS ---")
for row in conn.execute("SELECT id, name FROM organizations"):
    print(dict(row))

print("\n--- CATEGORIES ---")
try:
    for row in conn.execute("SELECT id, name, org_id, organization_id FROM categories"):
        print(dict(row))
except Exception as e:
    print(f"Error querying categories: {e}")
    for row in conn.execute("SELECT id, name, organization_id FROM categories"):
        print(dict(row))
