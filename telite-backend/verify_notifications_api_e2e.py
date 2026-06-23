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
from app.repositories.notification_repo import NotificationRepository

BASE_URL = "http://127.0.0.1:8000"

def run():
    uid = str(uuid.uuid4())[:8]
    org_slug = f"api-org-{uid}"
    
    # 1. Setup Data
    print("Setting up test data...")
    with get_platform_session() as platform_db:
        org = Organization(
            name=f"API Test Org {uid}",
            slug=org_slug,
            plan="enterprise",
            status="active",
            type="school",
            domain=f"api-{uid}.example.com"
        )
        platform_db.add(org)
        platform_db.commit()
        org_id = org.id

        password_clear = "password123"
        user_id = str(uuid.uuid4())
        u = User(
            id=user_id,
            username=f"api_user_{uid}",
            email=f"api_user_{uid}@example.com",
            full_name="API User",
            avatar_initials="AU",
            gradient_start="A",
            gradient_end="B",
            password_hash=hash_password(password_clear),
            role="learner",
            org_id=org_id
        )
        platform_db.add(u)
        platform_db.commit()

    with get_tenant_session(org_id) as db:
        repo = NotificationRepository(db)
        n1 = repo.create(
            user_id=user_id,
            org_id=org_id,
            title="API Test 1",
            body="Body 1",
            notif_type="system"
        )
        n2 = repo.create(
            user_id=user_id,
            org_id=org_id,
            title="API Test 2",
            body="Body 2",
            notif_type="system"
        )
        db.commit()
        n1_id = n1.id

    # 2. Login
    print("Logging in...")
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/auth/login", data={
        "username": u.email,
        "password": password_clear,
        "org_slug": org_slug
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    print("Login successful.")

    # 3. Test API Endpoints
    print("Testing GET /api/v1/notifications")
    resp = session.get(f"{BASE_URL}/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    print(f"GET /api/v1/notifications payload: {data}")
    
    print("Testing GET /api/v1/notifications/unread-count")
    resp = session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert resp.status_code == 200
    count_data = resp.json()
    assert count_data["count"] == 2
    print(f"GET /api/v1/notifications/unread-count payload: {count_data}")

    print(f"Testing PATCH /api/v1/notifications/{n1_id}/read")
    resp = session.patch(f"{BASE_URL}/api/v1/notifications/{n1_id}/read")
    assert resp.status_code == 200
    print(f"PATCH payload: {resp.json()}")

    resp = session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert resp.json()["count"] == 1

    print("Testing POST /api/v1/notifications/read-all")
    resp = session.post(f"{BASE_URL}/api/v1/notifications/read-all")
    assert resp.status_code == 200
    print(f"POST payload: {resp.json()}")

    resp = session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert resp.json()["count"] == 0

    print("Testing GET /notifications (deprecated)")
    resp = session.get(f"{BASE_URL}/notifications")
    assert resp.status_code == 200, resp.text
    print("Management endpoint works.")

    print("ALL API TESTS PASSED.")

if __name__ == "__main__":
    run()
