import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.management.schemas import AdminPayload
from app.api.routes.management.admins import post_admin
from app.services.user_provisioning import UserProvisioningService
import asyncio

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        learner = db.query(User).filter(User.role == "learner").first()
        
        admin_token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )
        
        # 1. Test role change
        print("1. Testing role change...")
        req = AdminPayload(
            email=learner.email,
            username=learner.username,
            full_name=learner.full_name,
            role="category_admin",
            category_scope="test-category"
        )
        try:
            post_admin(req, org_id, admin_token, db)
            print("Role changed successfully.")
        except Exception as e:
            print(f"Role change failed: {e}")
            
        role_notif = db.query(Notification).filter(
            Notification.user_id == learner.id,
            Notification.type == "info",
            Notification.title == "Role Changed",
        ).first()
        print(f"Role Changed Notif: {'FOUND' if role_notif else 'MISSING'}")
        
        # Change role back
        req.role = "learner"
        req.category_scope = None
        try:
            post_admin(req, org_id, admin_token, db)
        except:
            pass
            
        # 2. Test user joined
        print("2. Testing user joined...")
        provision_svc = UserProvisioningService(db)
        inv = provision_svc.invite_learner(
            email="new_invitee@test.com",
            username="new_invitee",
            full_name="New Invitee",
            role="learner",
            org_id=org_id,
            actor=admin
        )
        db.commit()
        
        try:
            provision_svc.accept_invitation(token=inv.token, password="password123", full_name="New Invitee")
            print("Invitation accepted.")
        except Exception as e:
            print(f"Invitation accept failed: {e}")
            
        joined_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.type == "info",
            Notification.title == "User Joined",
        ).first()
        print(f"User Joined Notif: {'FOUND' if joined_notif else 'MISSING'}")

if __name__ == "__main__":
    run_verification()
