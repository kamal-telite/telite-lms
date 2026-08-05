import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.course import Course
from app.api.auth import TokenData
from app.api.routes.enrolments import approve_request, reject_request, RejectPayload
import time

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        if not admin:
            print("No admin found.")
            return
            
        token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )

        course = db.query(Course).first()
        
        # Create an enrollment request
        from app.repositories.enrollment_repo import EnrollmentRepository
        repo = EnrollmentRepository(db)
        
        test_email = f"test_approval_{int(time.time())}@example.com"
        req = repo.create_request(
            full_name="Test Approval",
            email=test_email,
            category_slug=course.category_slug,
            org_id=org_id,
            request_type="self"
        )
        db.commit()
        
        print(f"Created request {req.id}")
        
        try:
            result = approve_request(req.id, current_user=token, db=db)
            print(f"Approval result: {result}")
        except Exception as e:
            print(f"Failed to approve: {e}")
            import traceback
            traceback.print_exc()
            return
            
        # Verify notification
        from app.models.notification import Notification
        user_id = result["user_id"]
        notifs = db.query(Notification).filter(Notification.user_id == user_id).all()
        print(f"Found {len(notifs)} notifications for user {user_id}")
        for n in notifs:
            print(f"ID: {n.id}, Type: {n.type}, Title: {n.title}")

        # Now test rejection
        test_email_reject = f"test_reject_{int(time.time())}@example.com"
        
        # We need a user to receive the rejection, so we'll provision one first for test purposes
        from app.services.user_provisioning import UserProvisioningService
        from app.core.password_utils import hash_password
        user_reject = UserProvisioningService(db)._provision_identity(
            email=test_email_reject,
            username=f"testrej{int(time.time())}",
            full_name="Test Reject",
            role="learner",
            org_id=org_id,
            password_hash=hash_password("test"),
            category_scope=course.category_slug,
            invited_via="self",
            enrollment_type="self"
        )
        
        req2 = repo.create_request(
            full_name="Test Reject",
            email=test_email_reject,
            category_slug=course.category_slug,
            org_id=org_id,
            request_type="self"
        )
        db.commit()
        
        try:
            result2 = reject_request(req2.id, body=RejectPayload(reason="Not allowed"), current_user=token, db=db)
            print(f"Rejection result: {result2}")
        except Exception as e:
            print(f"Failed to reject: {e}")
            return
            
        # Verify notification
        notifs2 = db.query(Notification).filter(Notification.user_id == user_reject.id).all()
        print(f"Found {len(notifs2)} notifications for user {user_reject.id}")
        for n in notifs2:
            print(f"ID: {n.id}, Type: {n.type}, Title: {n.title}, Message: {n.body}")


if __name__ == "__main__":
    run_verification()
