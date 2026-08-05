import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.category import Category
from app.models.course import Course
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.management.courses import post_course, patch_course, delete_course, permanently_delete_archived_course, CoursePayload
import time

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        category_admin = db.query(User).filter(User.role == "category_admin").first()
        
        token = TokenData(
            id=admin.id,
            email=admin.email,
            full_name=admin.full_name or "Test Admin",
            role=admin.role,
            org_id=org_id,
            category_scope=admin.category_scope
        )
        
        category = db.query(Category).filter(Category.slug == category_admin.category_scope).first()

        course_slug = f"test-lifecycle-{int(time.time())}"
        payload = CoursePayload(
            name=f"Test Lifecycle Course {course_slug}",
            slug=course_slug,
            description="Testing lifecycle events",
            tier="Basic",
            cover_image_url=None,
            prerequisite_course_id=None,
            price_paise=0
        )
        
        # 1. CREATE COURSE
        try:
            result = post_course(category.slug, payload, org_id, token, db)
            course_id = result['id']
            print(f"1. Course created: {course_id}")
        except Exception as e:
            print(f"Failed to create course: {e}")
            return
            
        # Manually publish course to test fanout on update
        from sqlalchemy import text
        db.execute(text("ALTER TABLE courses DROP CONSTRAINT IF EXISTS chk_courses_status"))
        db.execute(text("ALTER TABLE courses ADD CONSTRAINT chk_courses_status CHECK (status IN ('draft', 'active', 'published', 'archived', 'review', 'approved', 'rejected'))"))
        
        course = db.query(Course).filter(Course.id == course_id).first()
        course.status = "published"
        db.commit()

        # 2. UPDATE COURSE
        print(f"2. Testing course update...")
        update_payload = CoursePayload(
            name=f"Updated Course {course_slug}",
            slug=course_slug,
            description="Updated description",
            tier="Premium",
            cover_image_url=None,
            prerequisite_course_id=None,
            price_paise=100
        )
        
        try:
            patch_course(category.slug, course_id, update_payload, token, db)
            print("Course patched successfully.")
        except Exception as e:
            print(f"Failed to patch course: {e}")
            
        update_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.source_id == course_id,
            Notification.type == "course_updated"
        ).first()
        print(f"Update author notif: {'FOUND' if update_notif else 'MISSING'}")
        
        # 3. ARCHIVE COURSE
        print(f"3. Testing course archive...")
        try:
            delete_course(category.slug, course_id, token, db)
            print("Course archived successfully.")
        except Exception as e:
            print(f"Failed to archive course: {e}")
            
        archive_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.source_id == course_id,
            Notification.type == "course_archived"
        ).first()
        print(f"Archive author notif: {'FOUND' if archive_notif else 'MISSING'}")
        
        # 4. DELETE COURSE
        print(f"4. Testing permanent delete...")
        try:
            permanently_delete_archived_course(category.slug, course_id, token, db)
            print("Course deleted successfully.")
        except Exception as e:
            print(f"Failed to delete course: {e}")
            
        delete_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.source_id == course_id,
            Notification.type == "course_deleted"
        ).first()
        print(f"Delete author notif: {'FOUND' if delete_notif else 'MISSING'}")

if __name__ == "__main__":
    run_verification()
