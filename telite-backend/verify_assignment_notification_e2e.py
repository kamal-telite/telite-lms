import sys
import uuid

import requests
from dotenv import load_dotenv
from sqlalchemy import text

from app.core.password_utils import hash_password
from app.db.engine import get_platform_session
from app.models.category import Category
from app.models.enrollment import EnrollmentRequest
from app.models.organization import Organization
from app.models.user import User


load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "password123"


def _login(email: str, org_slug: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": PASSWORD, "org_slug": org_slug},
    )
    if response.status_code != 200:
        print(f"Login failed for {email}: {response.text}")
        sys.exit(1)
    return session


def _assert_ok(response: requests.Response, label: str) -> None:
    if response.status_code not in (200, 201):
        print(f"{label} failed: {response.status_code} {response.text}")
        sys.exit(1)


def verify_assignment_notifications() -> None:
    uid = uuid.uuid4().hex[:8]
    org_slug = f"assign-org-{uid}"
    cat_slug = f"assign-cat-{uid}"

    print("\n[1] Setting up test users, category, and enrollment...")
    with get_platform_session() as db:
        org = Organization(
            name=f"Assignment Notification Org {uid}",
            slug=org_slug,
            plan="enterprise",
            status="active",
            type="school",
            domain=f"assignment-{uid}.example.com",
        )
        db.add(org)
        db.flush()

        admin = User(
            id=f"admin-{uid}",
            username=f"assign-admin-{uid}",
            email=f"assign-admin-{uid}@example.com",
            full_name="Assignment Admin",
            role="super_admin",
            password_hash=hash_password(PASSWORD),
            avatar_initials="AA",
            gradient_start="#111111",
            gradient_end="#222222",
            org_id=org.id,
            is_active=True,
        )
        learner = User(
            id=f"learner-{uid}",
            username=f"assign-learner-{uid}",
            email=f"assign-learner-{uid}@example.com",
            full_name="Assignment Learner",
            role="learner",
            password_hash=hash_password(PASSWORD),
            avatar_initials="AL",
            gradient_start="#111111",
            gradient_end="#222222",
            org_id=org.id,
            is_active=True,
        )
        other_learner = User(
            id=f"other-learner-{uid}",
            username=f"assign-other-{uid}",
            email=f"assign-other-{uid}@example.com",
            full_name="Other Learner",
            role="learner",
            password_hash=hash_password(PASSWORD),
            avatar_initials="OL",
            gradient_start="#111111",
            gradient_end="#222222",
            org_id=org.id,
            is_active=True,
        )
        category = Category(
            id=f"cat-{uid}",
            name="Assignment Notifications",
            slug=cat_slug,
            org_id=org.id,
            organization_id=org.id,
            status="active",
            org_type="school",
        )
        db.add_all([admin, learner, other_learner, category])
        db.flush()

        enrollment = EnrollmentRequest(
            id=f"enrol-{uid}",
            full_name=learner.full_name,
            email=learner.email,
            category_slug=cat_slug,
            request_type="manual",
            org_id=org.id,
            status="approved",
            requested_at="2026-06-22 00:00",
            reviewed_by=admin.id,
            reviewed_at="2026-06-22 00:00",
        )
        db.add(enrollment)
        db.commit()

    admin_session = _login(admin.email, org_slug)
    learner_session = _login(learner.email, org_slug)
    other_session = _login(other_learner.email, org_slug)

    print("[2] Creating course, module, and assignment block through APIs...")
    response = admin_session.post(
        f"{BASE_URL}/categories/{cat_slug}/courses",
        json={
            "name": "Assignment Notification Course",
            "slug": f"assignment-notification-course-{uid}",
            "description": "Course used to verify assignment grading notifications.",
            "tier": "free",
            "status": "published",
        },
    )
    _assert_ok(response, "Create course")
    course_id = response.json()["id"]

    response = admin_session.post(
        f"{BASE_URL}/authoring/courses/{course_id}/sections",
        json={"title": "Assignments", "sort_order": 0},
    )
    _assert_ok(response, "Create section")
    section_id = response.json()["id"]

    response = admin_session.post(
        f"{BASE_URL}/authoring/modules",
        json={
            "course_id": course_id,
            "section": 0,
            "section_id": section_id,
            "title": "Assignment Module",
            "module_type": "assignment",
        },
    )
    _assert_ok(response, "Create module")
    module_id = response.json()["module"]["id"]

    response = admin_session.post(
        f"{BASE_URL}/authoring/modules/{module_id}/blocks",
        json={
            "block_type": "assignment",
            "content": "Submit your assignment response.",
            "sort_order": 0,
        },
    )
    _assert_ok(response, "Create assignment block")
    block_id = response.json()["id"]

    print("[3] Submitting assignment as learner...")
    response = learner_session.post(
        f"{BASE_URL}/api/v1/learner/assignments/{block_id}/submit",
        json={"submission_text": "This is my completed assignment."},
    )
    _assert_ok(response, "Submit assignment")
    submission_id = response.json()["submission"]["id"]

    print("[4] Grading assignment as admin...")
    response = admin_session.post(
        f"{BASE_URL}/api/v1/admin/submissions/{submission_id}/grade",
        json={"grade": 88, "feedback": "Good work.", "returned": False},
    )
    _assert_ok(response, "Grade assignment")

    print("[5] Verifying learner notification payload...")
    response = learner_session.get(f"{BASE_URL}/api/v1/notifications")
    _assert_ok(response, "List learner notifications")
    notifications = response.json()["items"]
    graded = next((n for n in notifications if n["type"] == "assignment_graded" and n["source_id"] == str(submission_id)), None)
    if not graded:
        print(f"assignment_graded notification not found for learner. Notifications: {notifications}")
        sys.exit(1)

    metadata = graded["metadata_json"]
    expected_metadata = {
        "route": f"/learner/courses/{course_id}/assignments/{block_id}",
        "route_name": "learner_assignment",
        "course_id": course_id,
        "block_id": block_id,
        "submission_id": submission_id,
    }
    if metadata != expected_metadata:
        print(f"Metadata mismatch. Expected {expected_metadata}, got {metadata}")
        sys.exit(1)
    if graded["source_type"] != "assignment" or graded["source_id"] != str(submission_id):
        print(f"Source tracking mismatch: {graded}")
        sys.exit(1)
    print(f"Notification verified: {graded['title']} -> {metadata['route']}")

    print("[6] Verifying learner ownership and unread count...")
    response = other_session.get(f"{BASE_URL}/api/v1/notifications")
    _assert_ok(response, "List other learner notifications")
    other_notifications = response.json()["items"]
    leaked = [n for n in other_notifications if n["type"] == "assignment_graded" and n["source_id"] == str(submission_id)]
    if leaked:
        print(f"Notification leaked to another learner: {leaked}")
        sys.exit(1)

    response = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    _assert_ok(response, "Get unread count")
    if response.json()["count"] != 1:
        print(f"Expected unread count 1, got {response.text}")
        sys.exit(1)

    response = learner_session.patch(f"{BASE_URL}/api/v1/notifications/{graded['id']}/read")
    _assert_ok(response, "Mark notification read")
    response = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    _assert_ok(response, "Get unread count after mark-read")
    if response.json()["count"] != 0:
        print(f"Expected unread count 0 after mark-read, got {response.text}")
        sys.exit(1)

    print("[7] Verifying re-grade creates a second notification...")
    response = admin_session.post(
        f"{BASE_URL}/api/v1/admin/submissions/{submission_id}/grade",
        json={"grade": 94, "feedback": "Updated score.", "returned": False},
    )
    _assert_ok(response, "Re-grade assignment")
    response = learner_session.get(f"{BASE_URL}/api/v1/notifications")
    _assert_ok(response, "List learner notifications after re-grade")
    regrade_notifications = [
        n for n in response.json()["items"]
        if n["type"] == "assignment_graded" and n["source_id"] == str(submission_id)
    ]
    if len(regrade_notifications) != 2:
        print(f"Expected 2 assignment_graded notifications after re-grade, got {len(regrade_notifications)}")
        sys.exit(1)

    response = learner_session.get(f"{BASE_URL}/api/v1/notifications/unread-count")
    _assert_ok(response, "Get unread count after re-grade")
    if response.json()["count"] != 1:
        print(f"Expected unread count 1 after re-grade, got {response.text}")
        sys.exit(1)

    with get_platform_session() as db:
        db_count = db.execute(
            text(
                "SELECT COUNT(*) FROM notifications "
                "WHERE user_id = :user_id AND type = 'assignment_graded' "
                "AND source_type = 'assignment' AND source_id = :source_id"
            ),
            {"user_id": learner.id, "source_id": str(submission_id)},
        ).scalar_one()
        if db_count != 2:
            print(f"Expected 2 DB notifications, got {db_count}")
            sys.exit(1)

    print("\nALL ASSIGNMENT NOTIFICATION TESTS PASSED.")


if __name__ == "__main__":
    verify_assignment_notifications()
