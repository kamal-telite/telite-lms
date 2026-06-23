import sys
import uuid

import requests
from dotenv import load_dotenv
from sqlalchemy import text

from app.core.password_utils import hash_password
from app.db.engine import get_platform_session
from app.models.organization import Organization
from app.models.user import User


load_dotenv(".env")

BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "password123"


def _assert_ok(response: requests.Response, label: str) -> None:
    if response.status_code not in (200, 201):
        print(f"{label} failed: {response.status_code} {response.text}")
        sys.exit(1)


def _login(email: str, org_slug: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": PASSWORD, "org_slug": org_slug},
    )
    _assert_ok(response, f"Login {email}")
    return session


def _create_org_admin(uid: str, label: str) -> tuple[Organization, User]:
    with get_platform_session() as db:
        org = Organization(
            name=f"QB Taxonomy {label} {uid}",
            slug=f"qb-tax-{label}-{uid}",
            plan="enterprise",
            status="active",
            type="school",
            domain=f"qb-tax-{label}-{uid}.example.com",
        )
        db.add(org)
        db.flush()
        admin = User(
            id=f"qb-admin-{label}-{uid}",
            username=f"qb-admin-{label}-{uid}",
            email=f"qb-admin-{label}-{uid}@example.com",
            full_name=f"QB Admin {label}",
            role="super_admin",
            password_hash=hash_password(PASSWORD),
            avatar_initials="QA",
            gradient_start="#111111",
            gradient_end="#222222",
            org_id=org.id,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        return org, admin


def _create_question(session: requests.Session, bank_id: int, payload: dict) -> dict:
    response = session.post(f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions", json=payload)
    _assert_ok(response, "Create question")
    return response.json()


def verify_question_bank_taxonomy() -> None:
    uid = uuid.uuid4().hex[:8]
    org_a, admin_a = _create_org_admin(uid, "a")
    org_b, admin_b = _create_org_admin(uid, "b")
    session_a = _login(admin_a.email, org_a.slug)
    session_b = _login(admin_b.email, org_b.slug)

    print("\n[1] Creating question bank, categories, and tags...")
    response = session_a.post(f"{BASE_URL}/api/v1/question-banks", json={"name": f"Taxonomy Bank {uid}"})
    _assert_ok(response, "Create question bank")
    bank_id = response.json()["id"]

    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/categories", json={"name": "Science"})
    _assert_ok(response, "Create parent category")
    science_id = response.json()["id"]
    response = session_a.post(
        f"{BASE_URL}/api/v1/question-banks/categories",
        json={"name": "Physics", "parent_id": science_id},
    )
    _assert_ok(response, "Create child category")
    physics_id = response.json()["id"]

    response = session_a.put(
        f"{BASE_URL}/api/v1/question-banks/categories/{physics_id}",
        json={"name": "Physical Science", "parent_id": science_id},
    )
    _assert_ok(response, "Update category")
    physics_id = response.json()["id"]

    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/tags", json={"name": "exam-ready"})
    _assert_ok(response, "Create tag")
    exam_tag_id = response.json()["id"]
    response = session_a.put(f"{BASE_URL}/api/v1/question-banks/tags/{exam_tag_id}", json={"name": "board-exam"})
    _assert_ok(response, "Update tag")
    exam_tag_id = response.json()["id"]

    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/tags", json={"name": "conceptual"})
    _assert_ok(response, "Create second tag")
    conceptual_tag_id = response.json()["id"]

    response = session_a.get(f"{BASE_URL}/api/v1/question-banks/categories")
    _assert_ok(response, "List category tree")
    category_tree = response.json()["items"]
    if not category_tree or category_tree[0]["children"][0]["id"] != physics_id:
        print(f"Category tree shape invalid: {category_tree}")
        sys.exit(1)

    print("[2] Creating taxonomy-assigned questions...")
    photosynthesis = _create_question(session_a, bank_id, {
        "category_id": physics_id,
        "tag_ids": [exam_tag_id, conceptual_tag_id],
        "question_type": "multiple_choice",
        "question_text": "Photosynthesis converts light into chemical energy.",
        "points": 2,
        "options_json": [{"id": "a", "text": "True"}, {"id": "b", "text": "False"}],
        "correct_answer_json": ["a"],
    })
    newton = _create_question(session_a, bank_id, {
        "category_id": science_id,
        "tag_ids": [conceptual_tag_id],
        "question_type": "essay",
        "question_text": "Explain Newton's second law of motion.",
        "points": 5,
        "options_json": [],
        "correct_answer_json": [],
    })

    print("[3] Verifying server-side filters and pagination...")
    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/questions",
        params={"search": "photosynthesis", "page": 1, "page_size": 50},
    )
    _assert_ok(response, "Filter by search")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["id"] != photosynthesis["id"]:
        print(f"Search filter mismatch: {data}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"category_id": physics_id, "tag_id": exam_tag_id, "version_state": "DRAFT"},
    )
    _assert_ok(response, "Filter by category/tag/draft")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["tag_ids"] != [exam_tag_id, conceptual_tag_id]:
        print(f"Category/tag filter mismatch: {data}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"question_type": "essay", "page_size": 1},
    )
    _assert_ok(response, "Filter by question type")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["id"] != newton["id"] or data["page_size"] != 1:
        print(f"Question type/pagination mismatch: {data}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"sort_by": "question_text", "sort_order": "asc", "page_size": 10},
    )
    _assert_ok(response, "Sort questions ascending by text")
    data = response.json()
    sorted_texts = [item["question_text"] for item in data["items"]]
    if sorted_texts != sorted(sorted_texts):
        print(f"Ascending sort mismatch: {sorted_texts}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"sort_by": "question_text", "sort_order": "desc", "page_size": 10},
    )
    _assert_ok(response, "Sort questions descending by text")
    data = response.json()
    sorted_texts = [item["question_text"] for item in data["items"]]
    if sorted_texts != sorted(sorted_texts, reverse=True):
        print(f"Descending sort mismatch: {sorted_texts}")
        sys.exit(1)

    print("[4] Publishing question and filtering by QuestionVersion.status...")
    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions/{photosynthesis['id']}/publish")
    _assert_ok(response, "Publish question")
    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"version_state": "PUBLISHED", "tag_id": exam_tag_id},
    )
    _assert_ok(response, "Filter published question")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["status"] != "PUBLISHED":
        print(f"Published filter mismatch: {data}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={"status": "PUBLISHED", "tag_id": exam_tag_id},
    )
    _assert_ok(response, "Filter published question via deprecated status alias")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["status"] != "PUBLISHED":
        print(f"Deprecated status alias mismatch: {data}")
        sys.exit(1)

    print("[5] Verifying cross-filter composition uses AND semantics...")
    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={
            "category_id": physics_id,
            "tag_id": exam_tag_id,
            "version_state": "PUBLISHED",
            "search": "photosynthesis",
        },
    )
    _assert_ok(response, "Filter by category/tag/status/search")
    data = response.json()
    if data["total"] != 1 or data["items"][0]["id"] != photosynthesis["id"]:
        print(f"Composed positive filter mismatch: {data}")
        sys.exit(1)

    response = session_a.get(
        f"{BASE_URL}/api/v1/question-banks/{bank_id}/questions",
        params={
            "category_id": science_id,
            "tag_id": exam_tag_id,
            "version_state": "PUBLISHED",
            "search": "photosynthesis",
        },
    )
    _assert_ok(response, "Filter by mismatched category/tag/status/search")
    data = response.json()
    if data["total"] != 0:
        print(f"Composed negative filter should be empty if filters are ANDed: {data}")
        sys.exit(1)

    print("[6] Verifying delete protection...")
    response = session_a.delete(f"{BASE_URL}/api/v1/question-banks/categories/{physics_id}")
    if response.status_code != 409:
        print(f"Expected category delete 409, got {response.status_code}: {response.text}")
        sys.exit(1)
    response = session_a.delete(f"{BASE_URL}/api/v1/question-banks/tags/{exam_tag_id}")
    if response.status_code != 409:
        print(f"Expected tag delete 409, got {response.status_code}: {response.text}")
        sys.exit(1)

    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/categories", json={"name": "Unused"})
    _assert_ok(response, "Create unused category")
    unused_category_id = response.json()["id"]
    response = session_a.delete(f"{BASE_URL}/api/v1/question-banks/categories/{unused_category_id}")
    _assert_ok(response, "Delete unused category")

    response = session_a.post(f"{BASE_URL}/api/v1/question-banks/tags", json={"name": "unused"})
    _assert_ok(response, "Create unused tag")
    unused_tag_id = response.json()["id"]
    response = session_a.delete(f"{BASE_URL}/api/v1/question-banks/tags/{unused_tag_id}")
    _assert_ok(response, "Delete unused tag")

    print("[7] Verifying import taxonomy metadata...")
    response = session_a.post(
        f"{BASE_URL}/api/v1/question-banks/imports",
        json={"file_key": f"imports/{uid}.csv", "category_id": science_id, "tag_ids": [conceptual_tag_id]},
    )
    _assert_ok(response, "Create import job")
    import_job = response.json()
    if import_job["metadata_json"]["category_id"] != science_id or import_job["metadata_json"]["tag_ids"] != [conceptual_tag_id]:
        print(f"Import taxonomy metadata mismatch: {import_job}")
        sys.exit(1)
    with get_platform_session() as db:
        metadata = db.execute(
            text("SELECT metadata_json FROM question_import_jobs WHERE id = :id"),
            {"id": import_job["id"]},
        ).scalar_one()
        if metadata["category_id"] != science_id or metadata["tag_ids"] != [conceptual_tag_id]:
            print(f"Persisted import metadata mismatch: {metadata}")
            sys.exit(1)

    print("[8] Verifying tenant isolation...")
    response = session_b.get(f"{BASE_URL}/api/v1/question-banks/categories")
    _assert_ok(response, "List other tenant categories")
    if response.json()["items"]:
        print(f"Other tenant saw categories it should not see: {response.json()}")
        sys.exit(1)

    response = session_b.post(f"{BASE_URL}/api/v1/question-banks", json={"name": f"Other Tenant Bank {uid}"})
    _assert_ok(response, "Create other tenant bank")
    other_bank_id = response.json()["id"]
    response = session_b.post(f"{BASE_URL}/api/v1/question-banks/{other_bank_id}/questions", json={
        "category_id": physics_id,
        "tag_ids": [exam_tag_id],
        "question_type": "multiple_choice",
        "question_text": "Cross tenant taxonomy attempt.",
        "points": 1,
        "options_json": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
        "correct_answer_json": ["a"],
    })
    if response.status_code != 400:
        print(f"Expected cross-tenant taxonomy assignment to fail with 400, got {response.status_code}: {response.text}")
        sys.exit(1)

    print("\nALL QUESTION BANK TAXONOMY TESTS PASSED.")


if __name__ == "__main__":
    verify_question_bank_taxonomy()
