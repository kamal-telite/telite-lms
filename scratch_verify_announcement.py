import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "telite-backend")))

from app.db.engine import get_tenant_session
from app.models.user import User
from app.models.notification import Notification
from app.api.auth import TokenData
from app.api.routes.announcements import _create_announcement_notifications
from app.workers.notification_tasks import dispatch_fanout_task
from app.models.announcement import Announcement, AnnouncementAudience

class DummyAnnouncement:
    def __init__(self, id, title, body):
        self.id = id
        self.title = title
        self.body = body

def run_verification():
    org_id = 1
    
    with get_tenant_session(org_id) as db:
        admin = db.query(User).filter(User.role == "super_admin").first()
        
        print("1. Creating dummy announcement...")
        ann = Announcement(
            org_id=org_id,
            title="Test Announcement",
            body="Test Body",
            created_by=admin.id
        )
        db.add(ann)
        db.commit()
        
        # Audience targeting super_admin role
        aud = AnnouncementAudience(
            announcement_id=ann.id,
            audience_type="role",
            audience_value="super_admin",
            org_id=org_id
        )
        db.add(aud)
        db.commit()
        
        print("2. Calling _create_announcement_notifications...")
        _create_announcement_notifications(db, ann, org_id)
        
        print("3. Firing Celery task directly for testing (synchronously)...")
        # In a real app this uses .delay(), but we can invoke the python function directly
        context = {
            "announcement_id": ann.id,
            "title": ann.title,
            "body": ann.body
        }
        audience_dict = {
            "type": aud.audience_type,
            "value": aud.audience_value
        }
        dispatch_fanout_task(
            event_name="announcement.published",
            org_id=org_id,
            context=context,
            audience=audience_dict
        )
        
        ann_notif = db.query(Notification).filter(
            Notification.user_id == admin.id,
            Notification.title == f"New Announcement: {ann.title}",
        ).first()
        print(f"Announcement Notif: {'FOUND' if ann_notif else 'MISSING'}")

if __name__ == "__main__":
    run_verification()
