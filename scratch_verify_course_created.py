import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.category import Category
from app.api.auth import TokenData
from app.api.routes.management.courses import post_course, CoursePayload
import time

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        category_admin = db.query(User).filter(User.role == "category_admin").first()
        
        if not admin or not category_admin:
            print("Missing admins")
            return
            
        token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )

        category = db.query(Category).filter(Category.slug == category_admin.category_scope).first()
        if not category:
            print("No category found.")
            return
            
        course_slug = f"test-course-{int(time.time())}"
        payload = CoursePayload(
            name=f"Test Course {course_slug}",
            slug=course_slug,
            description="A test course",
            tier="Basic",
            cover_image_url=None,
            prerequisite_course_id=None,
            price_paise=0
        )
        
        try:
            result = post_course(
                category_slug=category.slug,
                body=payload,
                org_id=org_id,
                current_user=token,
                db=db
            )
            print(f"Course created: {result['id']}")
            course_id = result['id']
        except Exception as e:
            print(f"Failed to create course: {e}")
            import traceback
            traceback.print_exc()
            return
            
        # Verify notifications
        from app.models.notification import Notification
        
        print("Checking Author notification...")
        author_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.source_id == course_id,
            Notification.type == "course_created"
        ).first()
        print(f"Author notif: {'FOUND' if author_notif else 'MISSING'} ({author_notif.title if author_notif else ''})")
        
        print("Checking Category Admin notification...")
        cat_admin_notif = db.query(Notification).filter(
            Notification.user_id == category_admin.id,
            Notification.source_id == course_id,
            Notification.type == "course_created"
        ).first()
        print(f"Category Admin notif: {'FOUND' if cat_admin_notif else 'MISSING'} ({cat_admin_notif.title if cat_admin_notif else ''})")

if __name__ == "__main__":
    run_verification()
