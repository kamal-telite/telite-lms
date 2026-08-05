import sys
import os
import requests

# Assuming the backend is running locally at http://localhost:8000, 
# but wait, I can just use FastAPI TestClient
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "telite-backend"))

from fastapi.testclient import TestClient
from app.main import create_app
from app.db.engine import get_db_session
from app.models.user import User
from app.models.notification import Notification, NotificationType

app = create_app()
client = TestClient(app)

def run_verification():
    with get_db_session() as db:
        # Find a learner user to test with
        learner = db.query(User).filter(User.role == "learner").first()
        if not learner:
            print("No learner found for testing. Exiting.")
            return
            
        print(f"Testing with learner {learner.email} (ID: {learner.id})")
        
        # 1. Create a notification programmatically to simulate existing history
        from app.repositories.notification_repo import NotificationRepository
        repo = NotificationRepository(db)
        
        # Legacy notification with metadata routing
        notif_legacy = Notification(
            user_id=learner.id,
            org_id=learner.org_id,
            title="Legacy Notif",
            body="This is a legacy body",
            type="info",
            metadata_json='{"route": "/legacy/path"}',
            source_type="system",
            source_id="1"
        )
        db.add(notif_legacy)
        
        # New notification via repo
        notif_new = repo.create(
            user_id=learner.id,
            org_id=learner.org_id,
            title="New Notif",
            message="This is a new message",
            notif_type=NotificationType.TASK_ASSIGNED,
            source_type="task",
            source_id="task-123",
            metadata={"extra": "data"}
        )
        db.commit()
        
        # Authenticate as learner
        # Mocking authentication dependency or just creating a token
        from app.core.security import create_access_token
        token = create_access_token(
            payload={"sub": learner.id, "role": learner.role, "org_id": learner.org_id, "session_id": "test"}
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        # Fetch notifications
        response = client.get("/api/v1/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        print("\n--- API Response Verification ---")
        items = data.get("items", [])
        print(f"Total notifications retrieved: {len(items)}")
        
        found_legacy = False
        found_new = False
        
        for item in items:
            # Check canonical fields
            assert "message" in item, "Missing 'message' field"
            assert "body" not in item, "'body' field should not be exposed"
            assert "action_url" in item, "Missing 'action_url' field"
            
            if item["id"] == notif_legacy.id:
                found_legacy = True
                print(f"Legacy Notification Verified: message='{item['message']}', action_url='{item['action_url']}'")
                assert item["message"] == "This is a legacy body"
                assert item["action_url"] == "/legacy/path"
                assert "route" not in item["metadata_json"]
                
            elif item["id"] == notif_new.id:
                found_new = True
                print(f"New Notification Verified: message='{item['message']}', action_url='{item['action_url']}'")
                assert item["message"] == "This is a new message"
                assert item["action_url"] == "/learner/tasks"  # derived from TASK_ASSIGNED
                assert item["metadata_json"] == {"extra": "data"}
                
        assert found_legacy, "Legacy notification not found in response"
        assert found_new, "New notification not found in response"
        
        print("\n--- Unread Counts & Mark as Read Verification ---")
        res_unread = client.get("/api/v1/notifications/unread-count", headers=headers)
        unread_count = res_unread.json()["count"]
        assert unread_count >= 2, f"Unread count mismatch: {unread_count}"
        
        # Mark new notification as read
        res_read = client.patch(f"/api/v1/notifications/{notif_new.id}/read", headers=headers)
        assert res_read.status_code == 200
        
        res_verify = client.get("/api/v1/notifications/unread-count", headers=headers)
        new_unread = res_verify.json()["count"]
        print(f"Unread count dropped from {unread_count} to {new_unread}")
        assert new_unread == unread_count - 1
        
        print("\n✅ Verification Successful: Canonical contract adhered to perfectly.")
    
if __name__ == "__main__":
    run_verification()
