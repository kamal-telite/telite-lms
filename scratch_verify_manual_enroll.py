import os
import sys

# Set up PYTHONPATH so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.course import Course
from app.api.auth import TokenData
from app.services.enrollment_service import EnrollmentService
import time

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        # Find an admin
        admin = db.query(User).filter(User.role == "super_admin").first()
        if not admin:
            admin = db.query(User).filter(User.role == "platform_admin").first()
            
        if not admin:
            print("No admin found.")
            return
            
        print(f"Using Admin: {admin.email}")
        
        # Find a course
        course = db.query(Course).first()
        if not course:
            print("No course found.")
            return
            
        print(f"Using Course: {course.name} ({course.id})")
        
        # Create a mock TokenData
        token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )
        
        # Perform manual enrollment
        service = EnrollmentService(db)
        
        test_email = f"test_manual_enroll_{int(time.time())}@example.com"
        try:
            result = service.manual_enroll(
                actor_token=token,
                full_name="Test Learner",
                email=test_email,
                course_ids=[course.id],
            )
            print(f"Manual enrollment successful. Enrolled course IDs: {result.enrolled_course_ids}")
        except Exception as e:
            print(f"Failed to enroll: {e}")
            import traceback
            traceback.print_exc()
            return
            
        db.commit()
        
        # Now check if the notification was created
        from app.models.notification import Notification
        
        notifs = db.query(Notification).filter(
            Notification.user_id == result.user.id
        ).all()
        
        print(f"Found {len(notifs)} notifications for learner {result.user.id}")
        for n in notifs:
            print(f"ID: {n.id}")
            print(f"Type: {n.type}")
            print(f"Title: {n.title}")
            print(f"Message: {n.body}")
            print(f"Source ID: {n.source_id}")
            print(f"Is Read: {n.is_read}")
            print(f"Action URL in API response: {n.to_dict().get('action_url')}")
            
if __name__ == "__main__":
    run_verification()
