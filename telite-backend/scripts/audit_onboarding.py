import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select, func
from app.db.engine import get_session_factory
from app.models.user import User
from app.models.pending_verification import PendingVerification
from app.models.invitation import OrgInvitation

def run_audits():
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        print("=== Audit: Global Username Uniqueness ===")
        duplicates = session.execute(
            text("SELECT username, COUNT(*) FROM users GROUP BY username HAVING COUNT(*) > 1")
        ).fetchall()
        print("Duplicates found:", duplicates)
        
        print("\n=== Audit: Users Status Anomalies ===")
        status_counts = session.execute(
            select(User.status, func.count(User.id)).group_by(User.status)
        ).fetchall()
        print("Status counts:", status_counts)
        
        print("\n=== Audit: Table Sizes ===")
        inv_count = session.execute(select(func.count(OrgInvitation.id))).scalar()
        print("org_invitations count:", inv_count)
        
        pv_count = session.execute(select(func.count(PendingVerification.id))).scalar()
        print("pending_verifications count:", pv_count)

if __name__ == "__main__":
    run_audits()
