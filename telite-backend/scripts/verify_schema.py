"""Phase 1 schema verification script."""

from app.services.store import get_conn, get_db_backend, get_table_columns, init_db


init_db()

with get_conn() as conn:
    print("=" * 50)
    print("PHASE 1 SCHEMA VERIFICATION")
    print("=" * 50)
    print(f"[0] Active DB backend: {get_db_backend()}")

    org_count = conn.execute("SELECT COUNT(*) AS c FROM organizations").fetchone()["c"]
    print(f"[1] Organizations count: {org_count}  (expected >= 2)")

    null_org = conn.execute("SELECT COUNT(*) AS c FROM users WHERE org_id IS NULL").fetchone()["c"]
    print(f"[2] Users with NULL org_id: {null_org}  (expected 0)")

    ff_count = conn.execute("SELECT COUNT(*) AS c FROM org_feature_flags").fetchone()["c"]
    print(f"[3] Feature flags total: {ff_count}  (expected >= 12)")

    global_admin = conn.execute(
        "SELECT is_platform_admin, role FROM users WHERE username = 'globaladmin'"
    ).fetchone()
    if global_admin:
        print(f"[4] Global admin: is_platform_admin={global_admin['is_platform_admin']}, role={global_admin['role']}")
    else:
        print("[4] Global admin user not found!")

    super_admin = conn.execute(
        "SELECT is_platform_admin, role FROM users WHERE username = 'superadmin'"
    ).fetchone()
    if super_admin:
        print(f"[4b] Superadmin: is_platform_admin={super_admin['is_platform_admin']}, role={super_admin['role']}")
    else:
        print("[4b] Superadmin user not found!")

    for table in ["org_feature_flags", "moodle_tenants", "org_invitations"]:
        columns = get_table_columns(conn, table)
        print(f"[5] Table {table}: {len(columns)} columns - {columns}")

    organization_columns = get_table_columns(conn, "organizations")
    print(f"[6] organizations columns: {organization_columns}")

    user_columns = get_table_columns(conn, "users")
    user_tenant_columns = [
        column
        for column in user_columns
        if column in ("org_id", "is_platform_admin", "status", "invited_via", "last_login_at")
    ]
    print(f"[7] users tenant columns: {user_tenant_columns}")

    for table in ["courses", "enrollment_requests", "tasks", "categories"]:
        columns = get_table_columns(conn, table)
        print(f"[8] {table} has org_id: {'org_id' in columns}")

    audit_columns = get_table_columns(conn, "audit_log")
    audit_tenant_columns = [
        column
        for column in audit_columns
        if column in ("org_id", "severity", "ip_address", "metadata_json")
    ]
    print(f"[9] audit_log tenant columns: {audit_tenant_columns}")

    orgs = conn.execute("SELECT id, name, slug, status FROM organizations ORDER BY id").fetchall()
    for org in orgs:
        print(f"[10] Org {org['id']}: name={org['name']}, slug={org['slug']}, status={org['status']}")

    print("=" * 50)
    print("PHASE 1 VERIFICATION COMPLETE")
    print("=" * 50)
