import sys
import os
from pathlib import Path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import engine
from app.core.password_utils import hash_password as get_password_hash
from sqlalchemy import text
from datetime import datetime
import json

class ResultWrapper:
    def __init__(self, res):
        self.res = res
    def fetchone(self):
        try:
            row = self.res.fetchone()
            return row._mapping if row else None
        except Exception:
            return None
    def fetchall(self):
        try:
            return [r._mapping for r in self.res.fetchall()]
        except Exception:
            return []

class ConnWrapper:
    def __init__(self):
        from sqlalchemy.orm import Session
        self.session = Session(engine.get_engine())
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.session.commit()
        self.session.close()
    def execute(self, query, params=()):
        if params:
            q = query
            p_dict = {}
            for i, p in enumerate(params):
                q = q.replace("?", f":p{i}", 1)
                p_dict[f"p{i}"] = p
            result = self.session.execute(text(q), p_dict)
        else:
            result = self.session.execute(text(query))
        return ResultWrapper(result)
    def commit(self):
        self.session.commit()

class TestStore:
    def get_conn(self):
        return ConnWrapper()
    def hash_password(self, pwd):
        return get_password_hash(pwd)
    def now_local(self):
        return datetime.utcnow().isoformat()
    def upsert_moodle_tenant(self, org_id, tenant_id):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO moodle_tenants (org_id, moodle_tenant_id, sync_status) VALUES (?, ?, 'pending') ON CONFLICT (org_id) DO UPDATE SET moodle_tenant_id = EXCLUDED.moodle_tenant_id", (org_id, tenant_id))
    def update_moodle_tenant_sync(self, org_id, status):
        with self.get_conn() as conn:
            conn.execute("UPDATE moodle_tenants SET sync_status = ? WHERE org_id = ?", (status, org_id))
    def create_moodle_sync_log(self, org_id, event_type, status, message, **kwargs):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO moodle_sync_logs (org_id, event_type, status, message, metadata_json) VALUES (?, ?, ?, ?, ?)", (org_id, event_type, status, message, json.dumps(kwargs)))
    def create_invitation(self, org_id, email, role, invited_by):
        import secrets
        token = secrets.token_hex(16)
        with self.get_conn() as conn:
            conn.execute("INSERT INTO org_invitations (org_id, email, role, token, invited_by_id) VALUES (?, ?, ?, ?, ?)", (org_id, email, role, token, invited_by))
        return {"token": token, "email": email, "id": 1}
    def write_platform_audit(self, action, target_id, **kwargs):
        with self.get_conn() as conn:
            conn.execute("INSERT INTO audit_log (action, target_id, metadata_json) VALUES (?, ?, ?)", (action, target_id, json.dumps(kwargs)))

if __name__ == "__main__":
    os.environ["TELITE_DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5432/telite_backend"
    store = TestStore()
    with store.get_conn() as conn:
        res = conn.execute("SELECT 1 as num, ? as text", ("hello",))
        print(res.fetchone())
