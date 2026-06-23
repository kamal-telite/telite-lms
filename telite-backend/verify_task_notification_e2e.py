import asyncio
import os
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()

from app.db.engine import get_platform_session, get_tenant_session
from app.models.organization import Organization
from app.models.user import User
from app.core.password_utils import hash_password

BASE_URL = "http://127.0.0.1:8000"

def run():
    uid = str(uuid.uuid4())[:8]
    org_slug = f"task-org-{uid}"
    
    # 1. Setup Data
    print("Setting up test data...")
    with get_platform_session() as platform_db:
        org = Organization(
            name=f"Task Test Org {uid}",
            slug=org_slug,
            plan="enterprise",
            status="active",
            type="school",
            domain=f"task-{uid}.example.com"
        )
        platform_db.add(org)
        platform_db.commit()
        org_id = org.id

        password_clear = "password123"
        admin_id = str(uuid.uuid4())
        learner_id = str(uuid.uuid4())
        
        # Create Super Admin
        admin = User(
            id=admin_id,
            username=f"task_admin_{uid}",
            email=f"task_admin_{uid}@example.com",
            full_name="Task Admin",
            avatar_initials="TA",
            gradient_start="A",
            gradient_end="B",
            password_hash=hash_password(password_clear),
            role="super_admin",
            org_id=org_id
        )
        platform_db.add(admin)
        
        # Create Learner
        learner = User(
            id=learner_id,
            username=f"task_learner_{uid}",
            email=f"task_learner_{uid}@example.com",
            full_name="Task Learner",
            avatar_initials="TL",
            gradient_start="A",
            gradient_end="B",
            password_hash=hash_password(password_clear),
            role="learner",
            org_id=org_id
        )
        platform_db.add(learner)
        platform_db.commit()

    # 2. Login as Admin
    print("Logging in as Admin...")
    admin_session = requests.Session()
    resp = admin_session.post(f"{BASE_URL}/auth/login", data={
        "username": admin.email,
        "password": password_clear,
        "org_slug": org_slug
    })
    assert resp.status_code == 200

    # 3. Create Task & Assign to Learner
    print("Creating Task & Assigning...")
    resp = admin_session.post(f"{BASE_URL}/tasks", json={
        "title": "Please read Chapter 1",
        "description": "Read the chapter by tomorrow",
        "assigned_label": learner.full_name,
        "assigned_to_user_id": learner.id,
        "assignment_scope": "individual",
        "category_slug": "ats"
    })
    assert resp.status_code == 200, resp.text
    task_payload = resp.json()
    print(f"Task created successfully. ID: {task_payload.get('id')}")

    # 4. Login as Learner
    print("Logging in as Learner...")
    learner_session = requests.Session()
    resp = learner_session.post(f"{BASE_URL}/auth/login", data={
        "username": learner.email,
        "password": password_clear,
        "org_slug": org_slug
    })
    assert resp.status_code == 200

    # 5. Verify Notification via API
    print("Testing GET /api/v1/notifications for Learner")
    resp = learner_session.get(f"{BASE_URL}/api/v1/notifications")
    assert resp.status_code == 200
    notifs = resp.json()["items"]
    assert len(notifs) == 1
    n = notifs[0]
    n_id = n["id"]
    metadata = n.get("metadata_json") or {}
    assert n["type"] == "task_assigned"
    assert n["source_type"] == "task"
    assert n["source_id"] == task_payload.get("id")
    assert metadata["route"] == "/learner/tasks"
    assert metadata["route_name"] == "learner_tasks"
    print(f"Notification generated: {n['title']} (ID: {n_id})")

    # 6. Check Unread Count
    print("Testing GET /api/v1/notifications/unread-count")
    resp = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert resp.status_code == 200
    count = resp.json()["count"]
    assert count == 1
    print("Unread count is 1.")

    # 7. Mark Read
    print(f"Testing PATCH /api/v1/notifications/{n_id}/read")
    resp = learner_session.patch(f"{BASE_URL}/api/v1/notifications/{n_id}/read")
    assert resp.status_code == 200
    print("Notification marked read.")

    # 8. Verify Count Decremented
    resp = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert resp.status_code == 200
    count = resp.json()["count"]
    assert count == 0
    print("Unread count decremented to 0.")

    print("ALL TASK NOTIFICATION TESTS PASSED.")

if __name__ == "__main__":
    run()
