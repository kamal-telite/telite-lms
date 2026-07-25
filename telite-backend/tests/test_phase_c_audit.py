import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.enrollment import EnrollmentRequest
from app.models.course_version import CourseVersion
from app.models.course_progress import CourseProgress
from app.models.organization import Organization
from app.core.security import create_access_token


import uuid


def _ensure_org(db: Session, org_id: int):
    org = db.get(Organization, org_id)
    if org:
        return org
    org = Organization(
        id=org_id,
        name=f"Phase C Org {org_id}",
        type="company",
        domain=f"phase-c-org-{org_id}.test",
        slug=f"phase-c-org-{org_id}",
        status="active",
        plan="pro",
    )
    db.add(org)
    db.flush()
    return org

def _create_user(db: Session, email_prefix: str, org_id: int):
    _ensure_org(db, org_id)
    email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@test.com"
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=email,
        full_name="Test",
        role="learner",
        password_hash="hash",
        org_id=org_id,
        avatar_initials="TS", gradient_start="#000", gradient_end="#FFF"
    )
    db.add(user)
    db.flush()
    return user


def _create_admin_user(db: Session, org_id: int = 1, role: str = "category_admin"):
    _ensure_org(db, org_id)
    email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=email,
        full_name="Admin User",
        role=role,
        password_hash="hash",
        org_id=org_id,
        avatar_initials="AD",
        gradient_start="#000",
        gradient_end="#FFF",
    )
    db.add(user)
    db.flush()
    return user


def _enroll_user(db: Session, user_id: str, course_id: str, org_id: int):
    db.flush()
    # Fetch user email
    user = db.query(User).filter_by(id=user_id).first()
    course = db.query(Course).filter_by(id=course_id).first()
    enr = EnrollmentRequest(
        id=str(uuid.uuid4()),
        email=user.email,
        full_name="Test",
        category_slug=course.category_slug if course else "uncategorized",
        request_type="course",
        org_id=org_id,
        status="approved",
        requested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    )
    db.add(enr)
    if course:
        progress = CourseProgress(
            user_id=user_id,
            course_id=course_id,
            org_id=org_id,
            status="in_progress",
            completion_percentage=0.0,
            enrolled_version=1,
        )
        db.add(progress)
    db.flush()

def _create_course_with_block(db: Session, org_id: int, block_type: str, settings: dict):
    _ensure_org(db, org_id)
    course_id = f"course_1_{block_type}_{uuid.uuid4().hex[:8]}"
    course = Course(
        id=course_id, name="Test Course", org_id=org_id, status="published",
        category_slug="uncategorized", slug=f"test-course-{block_type}-{uuid.uuid4().hex[:8]}"
    )
    db.add(course)
    db.flush()
    
    section = CourseSection(course_id=course_id, title="Section 1", sort_order=0, org_id=org_id)
    db.add(section)
    db.flush()
    
    module = CourseModule(course_id=course_id, section_id=section.id, title="Mod 1", org_id=org_id, module_type="ux_hint")
    db.add(module)
    db.flush()
    
    block = LessonBlock(
        module_id=module.id, block_type=block_type, 
        metadata_json=settings, org_id=org_id
    )
    db.add(block)
    db.flush()
    return course_id, block.id


def _create_native_quiz_course(
    db: Session,
    *,
    org_id: int = 1,
    settings: dict | None = None,
    category_slug: str = "uncategorized",
):
    _ensure_org(db, org_id)
    quiz_settings = settings or {
        "passing_score": 80,
        "max_attempts": 3,
        "questions": [
            {
                "id": "q1",
                "text": "2+2?",
                "points": 10,
                "options": [{"id": "opt1", "text": "3"}, {"id": "opt2", "text": "4"}],
                "correct_option_id": "opt2",
            }
        ],
    }
    course_id = f"course_quiz_{uuid.uuid4().hex[:8]}"
    course = Course(
        id=course_id,
        name="Native Quiz Course",
        org_id=org_id,
        status="published",
        category_slug=category_slug,
        slug=f"native-quiz-{uuid.uuid4().hex[:8]}",
        tier="Basic",
    )
    db.add(course)
    db.flush()
    
    section = CourseSection(course_id=course_id, title="Section 1", sort_order=0, org_id=org_id)
    db.add(section)
    db.flush()
    
    module = CourseModule(
        course_id=course_id,
        section_id=section.id,
        title="Quiz Module",
        org_id=org_id,
        module_type="quiz",
        status="published",
    )
    db.add(module)
    db.flush()
    block = LessonBlock(
        module_id=module.id,
        block_type="quiz",
        metadata_json=quiz_settings,
        content="",
        org_id=org_id,
    )
    db.add(block)
    db.flush()
    snapshot = {
        "sections": [
            {
                "modules": [
                    {
                        "id": module.id,
                        "title": module.title,
                        "module_type": module.module_type,
                        "section_id": None,
                        "sort_order": 0,
                        "blocks": [
                            {
                                "id": block.id,
                                "module_id": module.id,
                                "block_type": "quiz",
                                "content": "",
                                "settings": quiz_settings,
                                "metadata_json": quiz_settings,
                                "sort_order": 0,
                            }
                        ],
                    }
                ]
            }
        ]
    }
    admin_user = _create_admin_user(db, org_id=org_id)
    _create_version(db, course_id, org_id=org_id, version_number=1, snapshot=snapshot, created_by=admin_user.id)
    return course, module, block

def _create_version(db: Session, course_id: str, org_id: int, version_number: int, snapshot: dict, created_by: str):
    v = CourseVersion(
        id=str(uuid.uuid4()),
        course_id=course_id,
        org_id=org_id,
        version_number=version_number,
        status="published",
        snapshot_json=snapshot,
        published_by=None,
        created_by=created_by
    )
    db.add(v)
    db.flush()
    return v
def test_tenant_isolation_attack(client: TestClient, db_session: Session):
    # Setup Org A and Org B
    user_a = _create_user(db_session, "user_a@org1.com", org_id=1)
    user_b = _create_user(db_session, "user_b@org2.com", org_id=2)
    
    course_b, block_b = _create_course_with_block(db_session, org_id=2, block_type="poll", settings={"question": "B?"})
    _enroll_user(db_session, user_a.id, course_b, org_id=1)  # Maliciously enrolled by some bug
    db_session.commit()
    
    token_a = create_access_token(payload={"sub": user_a.id, "org_id": 1})
    
    # Org A tries to access Org B's poll results
    response = client.get(
        f"/api/v1/learner/blocks/{block_b}/poll-results",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    # Should be 404 because block_b belongs to org 2
    assert response.status_code == 404


def test_save_native_quiz_block_without_bank_reference_metadata(client: TestClient, db_session: Session):
    admin_user = _create_admin_user(db_session, org_id=1)
    course_id = f"course_native_quiz_{uuid.uuid4().hex[:8]}"
    course = Course(
        id=course_id,
        name="Quiz Save Course",
        org_id=1,
        status="draft",
        category_slug="uncategorized",
        slug=f"quiz-save-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(course)
    db_session.flush()
    
    section = CourseSection(course_id=course_id, title="Section 1", sort_order=0, org_id=1)
    db_session.add(section)
    db_session.flush()
    
    module = CourseModule(
        course_id=course_id,
        section_id=section.id,
        title="Quiz Module",
        org_id=1,
        module_type="quiz"
    )
    db_session.add(module)
    db_session.commit()

    token = create_access_token(payload={"sub": admin_user.id, "org_id": admin_user.org_id})

    lock_resp = client.post(
        f"/authoring/courses/{course_id}/lock",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert lock_resp.status_code == 200, lock_resp.text

    payload = {
        "blocks": [
            {
                "module_id": module.id,
                "block_type": "quiz",
                "content": "",
                "settings": {
                    "passing_score": 80,
                    "max_attempts": 3,
                    "questions": [
                        {
                            "id": "q1",
                            "text": "2+2?",
                            "points": 10,
                            "options": [
                                {"id": "opt1", "text": "3"},
                                {"id": "opt2", "text": "4"}
                            ],
                            "correct_option_id": "opt2"
                        }
                    ]
                },
                "sort_order": 0,
                "is_deleted": False
            }
        ]
    }

    response = client.put(
        f"/authoring/courses/{course_id}/blocks",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    assert response.json().get("blocks")


def test_version_freeze_pinning(client: TestClient, db_session: Session):
    # Setup
    user = _create_user(db_session, "learner@v.com", org_id=1)
    course_id = f"course_version_test_{uuid.uuid4().hex[:8]}"
    course = Course(id=course_id, name="V Test", org_id=1, status="published", category_slug="uncategorized", slug=f"v-test-{uuid.uuid4().hex[:8]}")
    db_session.add(course)
    _enroll_user(db_session, user.id, course_id, org_id=1)
    progress = db_session.query(CourseProgress).filter_by(user_id=user.id, course_id=course_id).first()
    progress.enrolled_version = 1
    
    # Create V1
    admin_user = _create_admin_user(db_session, org_id=1)
    v1_snapshot = {
        "sections": [{"modules": [{"id": 1, "title": "Module 1", "module_type": "page", "blocks": [{"id": 100, "block_type": "poll", "settings": {"question": "V1"}}]}]}]
    }
    _create_version(db_session, course_id, org_id=1, version_number=1, snapshot=v1_snapshot, created_by=admin_user.id)
    db_session.commit()
    
    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    
    # Learner fetches course for the first time. They should be pinned to V1!
    res1 = client.get(f"/api/v1/learner/courses/{course_id}", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["sections"][0]["modules"][0]["content"][0]["settings"]["question"] == "V1"
    
    # Now Author creates V2
    v2_snapshot = {
        "sections": [{"modules": [{"id": 1, "title": "Module 1", "module_type": "page", "blocks": [{"id": 100, "block_type": "poll", "settings": {"question": "V2"}}]}]}]
    }
    _create_version(db_session, course_id, org_id=1, version_number=2, snapshot=v2_snapshot, created_by=admin_user.id)
    db_session.commit()
    
    # Learner fetches course again. Since they started on V1, they MUST remain on V1!
    res2 = client.get(f"/api/v1/learner/courses/{course_id}", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["sections"][0]["modules"][0]["content"][0]["settings"]["question"] == "V1"


def test_quiz_security_leakage(client: TestClient, db_session: Session):
    user = _create_user(db_session, "quiz@q.com", org_id=1)
    
    # We create a quiz inside a V1 snapshot
    quiz_settings = {
        "questions": [
            {"id": "q1", "text": "2+2?", "correct_option_id": "opt2", "explanation": "Math"}
        ]
    }
    
    course, _, _ = _create_native_quiz_course(db_session, org_id=1, settings=quiz_settings)
    _enroll_user(db_session, user.id, course.id, org_id=1)
    progress = db_session.query(CourseProgress).filter_by(user_id=user.id, course_id=course.id).first()
    progress.enrolled_version = 1
    db_session.commit()
    
    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    
    res = client.get(f"/api/v1/learner/courses/{course.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    
    # Inspect the network payload
    q_block = res.json()["sections"][0]["modules"][0]["content"][0]
    fetched_settings = q_block["settings"]
    
    # Verify correct answers are STRIPPED
    assert "correct_option_id" not in fetched_settings["questions"][0]
    assert "explanation" not in fetched_settings["questions"][0]


def test_native_quiz_submission_enforces_enrollment(client: TestClient, db_session: Session):
    user = _create_user(db_session, "quiz-no-enroll", org_id=1)
    _, _, block = _create_native_quiz_course(db_session, org_id=1)
    db_session.commit()

    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    res = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt2"}},
    )

    assert res.status_code in [403, 404]


def test_native_quiz_submission_rejects_cross_course_access(client: TestClient, db_session: Session):
    user = _create_user(db_session, "quiz-cross-course", org_id=1)
    allowed_course, _, _ = _create_native_quiz_course(db_session, org_id=1)
    _, _, forbidden_block = _create_native_quiz_course(db_session, org_id=1, category_slug="other-category")
    _enroll_user(db_session, user.id, allowed_course.id, org_id=1)
    db_session.commit()

    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    res = client.post(
        f"/api/v1/learner/blocks/{forbidden_block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt2"}},
    )

    assert res.status_code in [403, 404]


def test_native_quiz_max_attempts_enforced(client: TestClient, db_session: Session):
    user = _create_user(db_session, "quiz-attempts", org_id=1)
    course, _, block = _create_native_quiz_course(
        db_session,
        org_id=1,
        settings={
            "passing_score": 80,
            "max_attempts": 1,
            "questions": [
                {
                    "id": "q1",
                    "text": "2+2?",
                    "points": 10,
                    "options": [{"id": "opt1", "text": "3"}, {"id": "opt2", "text": "4"}],
                    "correct_option_id": "opt2",
                }
            ],
        },
    )
    _enroll_user(db_session, user.id, course.id, org_id=1)
    db_session.commit()

    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    first = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt1"}},
    )
    second = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt2"}},
    )

    assert first.status_code == 200
    assert first.json()["passed"] is False
    assert second.status_code == 403
    assert "attempts" in second.json()["detail"].lower()


def test_native_quiz_passing_score_enforced(client: TestClient, db_session: Session):
    user = _create_user(db_session, "quiz-pass-score", org_id=1)
    course, _, block = _create_native_quiz_course(
        db_session,
        org_id=1,
        settings={
            "passing_score": 80,
            "max_attempts": 0,
            "questions": [
                {
                    "id": "q1",
                    "text": "2+2?",
                    "points": 10,
                    "options": [{"id": "opt1", "text": "3"}, {"id": "opt2", "text": "4"}],
                    "correct_option_id": "opt2",
                },
                {
                    "id": "q2",
                    "text": "3+3?",
                    "points": 10,
                    "options": [{"id": "opt3", "text": "5"}, {"id": "opt4", "text": "6"}],
                    "correct_option_id": "opt4",
                },
            ],
        },
    )
    _enroll_user(db_session, user.id, course.id, org_id=1)
    db_session.commit()

    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    failing = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt2", "q2": "opt3"}},
    )
    passing = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "opt2", "q2": "opt4"}},
    )

    assert failing.status_code == 200
    assert failing.json()["score"] == 50
    assert failing.json()["passed"] is False
    assert passing.status_code == 200
    assert passing.json()["score"] == 100
    assert passing.json()["passed"] is True


def test_assignment_submission_ui_flow(client: TestClient, db_session: Session):
    user = _create_user(db_session, "assign@a.com", org_id=1)
    course_id, block_id = _create_course_with_block(db_session, org_id=1, block_type="assignment", settings={})
    _enroll_user(db_session, user.id, course_id, org_id=1)
    db_session.commit()
    
    token = create_access_token(payload={"sub": user.id, "org_id": 1})
    
    # Submit assignment
    res_sub = client.post(
        f"/api/v1/learner/assignments/{block_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"submission_text": "Here is my essay.", "asset_ids": []}
    )
    assert res_sub.status_code == 200
    
    # Fetch assignment block result
    res_get = client.get(
        f"/api/v1/learner/assignments/{block_id}/submission",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["submission"]["submission_text"] == "Here is my essay."
    assert data["submission"]["status"] == "pending_verification"
