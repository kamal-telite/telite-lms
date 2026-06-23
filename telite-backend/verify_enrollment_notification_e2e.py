import os
import sys
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"

# We will use the live postgres connection instead of overriding to sqlite.
from dotenv import load_dotenv
load_dotenv()

# Note: We do NOT need to insert records directly, we will use the API to do everything.
# Wait, actually creating a test organization and platform admin requires DB access.
from app.db.engine import get_platform_session
from app.models.organization import Organization
from app.models.user import User
from app.core.password_utils import hash_password

def setup_test_data():
    uid = uuid.uuid4().hex[:8]
    org_slug = f"enrollment-org-{uid}"
    admin_email = f"admin-{uid}@example.com"
    learner_email = f"learner-{uid}@example.com"
    password = "password123"

    with get_platform_session() as platform_db:
        # Create Org
        org = Organization(
            name=f"Enrollment Test Org {uid}",
            slug=org_slug,
            domain=f"{org_slug}.example.com",
            type="b2b",
        )
        platform_db.add(org)
        platform_db.flush()
        org_id = org.id

        # Create Admin
        admin = User(
            id=f"usr-{uuid.uuid4().hex[:10]}",
            email=admin_email,
            username=f"admin-{uid}",
            password_hash=hash_password(password),
            full_name="Enrollment Admin",
            role="super_admin",
            org_id=org_id,
            is_active=True,
            avatar_initials="EA",
            gradient_start="#000000",
            gradient_end="#FFFFFF",
        )
        platform_db.add(admin)

        # Create Learner
        learner = User(
            id=f"usr-{uuid.uuid4().hex[:10]}",
            email=learner_email,
            username=f"learner-{uid}",
            password_hash=hash_password(password),
            full_name="Enrollment Learner",
            role="learner",
            org_id=org_id,
            is_active=True,
            avatar_initials="EL",
            gradient_start="#000000",
            gradient_end="#FFFFFF",
        )
        platform_db.add(learner)
        platform_db.commit()

        # Create Category and Course directly since we are super admin
        from app.models.course import Course
        from app.models.category import Category
        
        category = Category(
            id=f"cat-{uuid.uuid4().hex[:10]}",
            slug=f"test-category-{uid}",
            name="Test Category",
            org_id=org_id,
        )
        platform_db.add(category)
        platform_db.flush()

        course = Course(
            id=f"crs-{uuid.uuid4().hex[:10]}",
            name="Introduction to E2E Testing",
            slug=f"intro-e2e-{uid}",
            category_slug=category.slug,
            org_id=org_id,
            status="published",
        )
        platform_db.add(course)
        platform_db.commit()

        return {
            "org_slug": org_slug,
            "org_id": org_id,
            "admin_email": admin_email,
            "learner_email": learner_email,
            "password": password,
            "admin_id": admin.id,
            "learner_id": learner.id,
            "course_id": course.id,
        }

def run_tests():
    print("Setting up test data...")
    test_data = setup_test_data()
    org_slug = test_data["org_slug"]

    admin_session = requests.Session()
    learner_session = requests.Session()

    print("\nLogging in as Admin...")
    admin_login = admin_session.post(f"{BASE_URL}/auth/login", data={
        "username": test_data["admin_email"],
        "password": test_data["password"],
        "org_slug": org_slug
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"

    print("Logging in as Learner...")
    learner_login = learner_session.post(f"{BASE_URL}/auth/login", data={
        "username": test_data["learner_email"],
        "password": test_data["password"],
        "org_slug": org_slug
    })
    assert learner_login.status_code == 200, f"Learner login failed: {learner_login.text}"

    # 1. Manual Enrollment
    print("\n[1] Testing Manual Enrollment...")
    manual_resp = admin_session.post(f"{BASE_URL}/api/v1/enrol/manual", json={
        "full_name": "Enrollment Learner",
        "email": test_data["learner_email"],
        "course_ids": [test_data["course_id"]]
    })
    assert manual_resp.status_code == 200, f"Manual enroll failed: {manual_resp.text}"
    print(f"Manual enrollment successful. Response: {manual_resp.json()['status']}")

    # 2. Check Notification for Manual Enrollment
    notifs_resp = learner_session.get(f"{BASE_URL}/api/v1/notifications")
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()["items"]
    assert len(notifs) == 1, f"Expected 1 notification, got {len(notifs)}"
    n = notifs[0]
    print(f"Notification received: {n['title']} - {n['body']}")
    assert n["type"] == "enrollment_created"
    assert n["source_type"] == "course"
    assert n["source_id"] == test_data["course_id"]
    
    metadata = n.get("metadata_json") or {}
    assert "route" in metadata
    assert metadata["route"] == f"/learner/courses/{test_data['course_id']}"
    assert metadata["route_name"] == "learner_course"

    unread_resp = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert unread_resp.json()["count"] == 1
    print("Unread count is exactly 1.")

    # 3. Idempotency Check (Manual Re-Enrollment)
    print("\n[2] Testing Idempotency (Re-Enrollment)...")
    manual_resp_2 = admin_session.post(f"{BASE_URL}/api/v1/enrol/manual", json={
        "full_name": "Enrollment Learner",
        "email": test_data["learner_email"],
        "course_ids": [test_data["course_id"]]
    })
    assert manual_resp_2.status_code == 200
    skipped = manual_resp_2.json()["skipped_course_ids"]
    assert len(skipped) == 1, "Expected the course to be skipped."
    print("Re-enrollment skipped successfully.")

    # Check that NO new notifications were created
    unread_resp_2 = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert unread_resp_2.json()["count"] == 1, "Unread count should STILL be 1!"
    print("Zero duplicate notifications generated.")

    # 4. Mark Read
    print("\n[3] Testing Mark Read...")
    read_resp = learner_session.patch(f"{BASE_URL}/api/v1/notifications/{n['id']}/read")
    assert read_resp.status_code == 200
    unread_resp_3 = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    assert unread_resp_3.json()["count"] == 0
    print("Unread count correctly decremented to 0.")

    # 5. Bulk Enrollment
    print("\n[4] Testing Bulk Enrollment (CSV Simulation)...")
    bulk_resp = admin_session.post(
        f"{BASE_URL}/api/v1/enrol/bulk/execute",
        json={
            "rows": [
                {
                    "name": "Bulk Learner",
                    "email": f"bulk_{test_data['learner_email']}",
                    "course_id": test_data["course_id"]
                }
            ]
        }
    )
    assert bulk_resp.status_code == 200, f"Bulk enroll failed: {bulk_resp.text}"
    print(f"Bulk enrollment processed.")

    # Check notification for the new bulk user
    bulk_learner_session = requests.Session()
    bulk_login = bulk_learner_session.post(f"{BASE_URL}/auth/login", json={
        "identifier": f"bulk_{test_data['learner_email']}",
        # Provisioning creates users without password or we can't login easily...
        # Let's bypass the login or query DB directly to prove tenant isolation and notification creation.
        # Actually, user provisioning creates a user. The default password might not be known.
        # So we query DB directly.
    })

    with get_platform_session() as platform_db:
        bulk_user = platform_db.query(User).filter_by(email=f"bulk_{test_data['learner_email']}").first()
        from app.models.notification import Notification
        bulk_notifs = platform_db.query(Notification).filter_by(user_id=bulk_user.id).all()
        assert len(bulk_notifs) == 1
        print("Bulk learner received exactly 1 notification in DB.")
        assert bulk_notifs[0].type == "enrollment_created"
        assert bulk_notifs[0].org_id == test_data["org_id"]

    # 6. Bulk Enrollment Idempotency
    print("\n[5] Testing Bulk Enrollment Idempotency...")
    bulk_resp_2 = admin_session.post(
        f"{BASE_URL}/api/v1/enrol/bulk/execute",
        json={
            "rows": [
                {
                    "name": "Bulk Learner",
                    "email": f"bulk_{test_data['learner_email']}",
                    "course_id": test_data["course_id"]
                }
            ]
        }
    )
    assert bulk_resp_2.status_code == 200
    with get_platform_session() as platform_db:
        bulk_notifs_2 = platform_db.query(Notification).filter_by(user_id=bulk_user.id).all()
        assert len(bulk_notifs_2) == 1, "Expected NO new notifications after duplicate bulk enrollment."
    print("Zero duplicate notifications generated for bulk enrollment.")

    print("\nALL ENROLLMENT NOTIFICATION TESTS PASSED.")

if __name__ == "__main__":
    run_tests()
