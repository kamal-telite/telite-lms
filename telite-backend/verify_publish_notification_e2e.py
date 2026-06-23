import os
import sys
import json
import uuid
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Add backend to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.engine import get_engine

load_dotenv()

BASE_URL = "http://localhost:8000"

def verify_publish_notifications():
    print("\nSetting up test data...")
    uid = uuid.uuid4().hex[:8]
    
    from app.db.engine import get_platform_session
    from app.models.organization import Organization
    from app.models.user import User
    from app.core.password_utils import hash_password

    with get_platform_session() as platform_db:
        # Get or create org
        org = platform_db.query(Organization).first()
        if not org:
            org = Organization(name="Test Org", slug=f"test-{uid}", type="b2b")
            platform_db.add(org)
            platform_db.flush()
        
        admin_email = f"admin-{uid}@test.com"
        admin = User(
            id=f"usr-{uid}",
            email=admin_email,
            username=f"admin-{uid}",
            password_hash=hash_password("password123"),
            full_name="Admin User",
            role="super_admin",
            org_id=org.id,
            is_active=True,
            avatar_initials="AD",
            gradient_start="#000000",
            gradient_end="#ffffff",
        )
        platform_db.add(admin)
        platform_db.commit()
    from app.models.course import Course
    from app.models.category import Category
    from app.models.course_version import CourseVersion
    
    with get_platform_session() as platform_db:
        cat_slug = f"pub-cat-{uid}"
        course_slug = f"pub-course-{uid}"
        
        category = Category(
            id=f"cat-{uuid.uuid4().hex[:10]}",
            slug=cat_slug,
            name="Test Publish Category",
            org_id=org.id,
        )
        platform_db.add(category)
        platform_db.flush()
        
        course_id = f"crs-{uuid.uuid4().hex[:10]}"
        course = Course(
            id=course_id,
            name="Test Publish Course",
            slug=course_slug,
            category_slug=category.slug,
            org_id=org.id,
            status="draft",
        )
        platform_db.add(course)
        platform_db.flush()
        
        draft = CourseVersion(
            id=f"cv-{uuid.uuid4().hex[:10]}",
            course_id=course_id,
            org_id=org.id,
            version_number=1,
            status="Draft",
        )
        platform_db.add(draft)
        platform_db.commit()

    with get_platform_session() as check_db:
        from app.models.user import User
        check_user = check_db.query(User).filter(User.username == f"admin-{uid}").first()
        print(f"\nDB check - User exists: {check_user is not None}, Email: {check_user.email if check_user else 'N/A'}")

    print("\nLogging in as Admin...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": f"admin-{uid}@test.com", "password": "password123", "org_slug": org.slug})
    if resp.status_code != 200:
        print("Login failed. Check your test database auth setup.")
        print(resp.text)
        sys.exit(1)
        
    admin_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Publish course directly
    print("\n[2] Publishing Course Directly...")
    resp = requests.post(f"{BASE_URL}/authoring/courses/{course_id}/publish", headers=headers)
    if resp.status_code != 200:
        print("Failed to publish course:", resp.text)
        sys.exit(1)

    print("\n[3] Verifying course_published notification...")
    with get_platform_session() as conn:
        all_notifs = conn.execute(text(f"""
            SELECT * FROM notifications ORDER BY created_at DESC LIMIT 5
        """)).fetchall()
        print(f"Last 5 notifications globally:")
        for row in all_notifs:
            print(dict(row._mapping))
            
        result = conn.execute(text(f"""
            SELECT title, body, metadata_json, source_type, source_id
            FROM notifications
            WHERE user_id = 'usr-{uid}' AND type = 'course_published'
            ORDER BY created_at DESC LIMIT 1
        """)).fetchone()
        
        if not result:
            print("ERROR: course_published notification not found.")
            sys.exit(1)
            
        print(f"Notification received: {result.title} - {result.body}")
        
        metadata = json.loads(result.metadata_json) if result.metadata_json else {}
        expected_route = f"/categories/{cat_slug}/builder/{course_id}"
        if metadata.get("route") != expected_route or metadata.get("route_name") != "category_course_builder":
            print(f"ERROR: Deep link route mismatch. Expected {expected_route}, got {metadata}")
            sys.exit(1)
        if metadata.get("course_version_id") != draft.id or metadata.get("version_number") != draft.version_number:
            print(f"ERROR: Course version metadata missing. Got {metadata}")
            sys.exit(1)
        if result.source_type != "course" or result.source_id != course_id:
            print(f"ERROR: Source tracking missing. Type: {result.source_type}, ID: {result.source_id}")
            sys.exit(1)

    # Test rejection workflow
    print("\n[4] Creating second course for Review/Reject Workflow...")
    course_slug_2 = f"reject-course-{uid}"
    resp = requests.post(f"{BASE_URL}/categories/{cat_slug}/courses", headers=headers, json={
        "name": "Test Reject Course",
        "slug": course_slug_2,
        "category_slug": cat_slug,
        "description": "A course to be rejected",
        "tier": "free",
    })
    if resp.status_code != 200:
        print("Failed to create reject course:", resp.text)
        sys.exit(1)
    course_id_2 = resp.json()["id"]

    resp = requests.post(f"{BASE_URL}/authoring/courses/{course_id_2}/sections", headers=headers, json={
        "title": "Review Section",
        "sort_order": 0,
    })
    if resp.status_code != 200:
        print("Failed to create review course section:", resp.text)
        sys.exit(1)
    section_id_2 = resp.json()["id"]

    resp = requests.post(f"{BASE_URL}/authoring/modules", headers=headers, json={
        "course_id": course_id_2,
        "section": 0,
        "section_id": section_id_2,
        "title": "Review Module",
        "module_type": "lesson",
    })
    if resp.status_code != 200:
        print("Failed to create review course module:", resp.text)
        sys.exit(1)
    module_id_2 = resp.json()["module"]["id"]

    resp = requests.post(f"{BASE_URL}/authoring/modules/{module_id_2}/blocks", headers=headers, json={
        "block_type": "heading",
        "content": "Review-ready content",
        "sort_order": 0,
    })
    if resp.status_code != 200:
        print("Failed to create review course block:", resp.text)
        sys.exit(1)

    print("\n[5] Submitting for review...")
    resp = requests.post(f"{BASE_URL}/authoring/publishing/courses/{course_id_2}/workflow", headers=headers, json={
        "action": "submit_for_review",
        "notes": "Please review"
    })
    if resp.status_code != 200:
        print("Failed to submit for review:", resp.text)
        sys.exit(1)

    print("\n[6] Rejecting course...")
    resp = requests.post(f"{BASE_URL}/authoring/publishing/courses/{course_id_2}/workflow", headers=headers, json={
        "action": "reject",
        "notes": "Needs more work"
    })
    if resp.status_code != 200:
        print("Failed to reject course:", resp.text)
        sys.exit(1)

    print("\n[7] Verifying course_rejected notification...")
    with get_platform_session() as conn:
        result = conn.execute(text(f"""
            SELECT title, body, metadata_json, source_type, source_id
            FROM notifications
            WHERE user_id = 'usr-{uid}' AND type = 'course_rejected'
            ORDER BY created_at DESC LIMIT 1
        """)).fetchone()
        
        if not result:
            print("ERROR: course_rejected notification not found.")
            sys.exit(1)
            
        print(f"Notification received: {result.title} - {result.body}")
        metadata = json.loads(result.metadata_json) if result.metadata_json else {}
        expected_route = f"/categories/{cat_slug}/builder/{course_id_2}"
        if metadata.get("route") != expected_route or metadata.get("route_name") != "category_course_builder":
            print(f"ERROR: Deep link route mismatch. Expected {expected_route}, got {metadata}")
            sys.exit(1)

    print("\nALL PUBLISHING NOTIFICATION TESTS PASSED.")

if __name__ == "__main__":
    verify_publish_notifications()
