import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.course import Course
from app.models.course_review import CourseReview
from app.api.auth import TokenData
from app.api.routes.publishing import execute_workflow_action, WorkflowActionRequest
from app.workers.notification_tasks import dispatch_fanout_task
import time
from datetime import datetime, timezone

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
        if not course:
            print("No course found.")
            return
            
        print(f"Testing publish for course {course.id}")
        
        from sqlalchemy import text
        db.execute(text("ALTER TABLE courses DROP CONSTRAINT IF EXISTS chk_courses_status"))
        db.execute(text("ALTER TABLE courses ADD CONSTRAINT chk_courses_status CHECK (status IN ('draft', 'active', 'published', 'archived', 'review', 'approved', 'rejected'))"))
        db.commit()
        
        # Fake a submit_for_review so there's an author
        course.status = "approved"
        
        review = CourseReview(
            course_id=course.id,
            action="submit_for_review",
            from_status="draft",
            to_status="in_review",
            reviewed_by=admin.id,
            reviewed_at=datetime.now(timezone.utc),
            org_id=org_id,
        )
        db.add(review)
        db.commit()
        
        try:
            result = execute_workflow_action(
                course_id=course.id,
                request=WorkflowActionRequest(action="publish", notes="Looks good"),
                current_user=token,
                db=db
            )
            print(f"Publish result: {result['success']}")
        except Exception as e:
            print(f"Failed to publish: {e}")
            import traceback
            traceback.print_exc()
            return
            
        # Verify direct notification to author
        from app.models.notification import Notification
        author_id = admin.id
        notifs = db.query(Notification).filter(Notification.user_id == author_id).order_by(Notification.created_at.desc()).all()
        found = False
        for n in notifs:
            if n.type == "course_published":
                found = True
                print(f"Author notification: ID {n.id}, Type: {n.type}, Title: {n.title}")
                break
        if not found:
            print("Failed to find author notification!")
            
        # Test fanout directly since celery might be off in this scratch script
        print("Testing fanout locally...")
        dispatch_fanout_task(
            event_name="course.published",
            org_id=org_id,
            context={
                "course_id": course.id,
                "course_name": course.name,
                "version": "1.0"
            },
            audience={
                "type": "category_enrolled",
                "category_slug": course.category_slug
            }
        )
        
        # Since it inserts directly, we should see notifications for all users in the category
        category_users = db.query(User).filter(User.category_scope == course.category_slug, User.is_active == True).all()
        print(f"Users in category '{course.category_slug}': {len(category_users)}")
        
        for u in category_users:
            fanout_notif = db.query(Notification).filter(Notification.user_id == u.id).order_by(Notification.created_at.desc()).first()
            if fanout_notif and fanout_notif.type == "course_published":
                print(f"Verified fanout for {u.email}: {fanout_notif.title}")
            else:
                print(f"No fanout notif for {u.email}")
                

if __name__ == "__main__":
    run_verification()
