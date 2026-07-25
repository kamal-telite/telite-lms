from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.core.security import create_access_token
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.course_version import CourseVersion
from app.models.enrollment import EnrollmentRequest
from app.models.gradebook import GradeItem, GradeResult
from app.models.lesson_block import LessonBlock
from app.models.organization import Organization
from app.models.user import User
from app.services.assignment_service import AssignmentService


ORG_ID = 7101


def _ensure_org(db: Session, org_id: int = ORG_ID) -> Organization:
    org = db.get(Organization, org_id)
    if org:
        return org
    org = Organization(
        id=org_id,
        name=f"Gradebook Org {org_id}",
        type="company",
        domain=f"gradebook-{org_id}.example.edu",
        slug=f"gradebook-{org_id}",
        status="active",
        plan="pro",
    )
    db.add(org)
    db.flush()
    return org


def _user(db: Session, role: str, *, org_id: int = ORG_ID, category_scope: str = "academics") -> User:
    _ensure_org(db, org_id)
    user_id = f"{role}-{uuid.uuid4().hex[:8]}"
    user = User(
        id=user_id,
        username=user_id,
        email=f"{user_id}@example.edu",
        full_name=f"{role} User",
        role=role,
        category_scope=category_scope,
        org_id=org_id,
        organization_id=org_id,
        password_hash="not-used",
        avatar_initials="GB",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    db.add(user)
    db.flush()
    return user


def _course_with_block(db: Session, *, block_type: str, settings: dict, org_id: int = ORG_ID):
    _ensure_org(db, org_id)
    course = Course(
        id=f"course-{uuid.uuid4().hex[:8]}",
        name="Gradebook Course",
        org_id=org_id,
        status="published",
        category_slug="academics",
        slug=f"gradebook-course-{uuid.uuid4().hex[:8]}",
        tier="Basic",
    )
    db.add(course)
    db.flush()
    module = CourseModule(
        course_id=course.id,
        title="Gradebook Module",
        org_id=org_id,
        module_type=block_type,
        status="published",
    )
    db.add(module)
    db.flush()
    block = LessonBlock(
        module_id=module.id,
        block_type=block_type,
        content=f"{block_type.title()} Block",
        metadata_json=settings,
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
                        "blocks": [
                            {
                                "id": block.id,
                                "module_id": module.id,
                                "block_type": block.block_type,
                                "content": block.content,
                                "settings": settings,
                                "metadata_json": settings,
                                "sort_order": 0,
                            }
                        ],
                    }
                ]
            }
        ]
    }
    admin = _user(db, "admin", org_id=org_id)
    db.add(
        CourseVersion(
            id=f"cv-{uuid.uuid4().hex[:8]}",
            course_id=course.id,
            org_id=org_id,
            version_number=1,
            status="published",
            created_by=admin.id,
            snapshot_json=snapshot,
        )
    )
    db.flush()
    return course, module, block


def _enroll(db: Session, user: User, course: Course, *, org_id: int = ORG_ID) -> None:
    db.add(
        EnrollmentRequest(
            id=str(uuid.uuid4()),
            email=user.email,
            full_name=user.full_name,
            category_slug=course.category_slug,
            request_type="course",
            org_id=org_id,
            status="approved",
            requested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        )
    )
    db.add(
        CourseProgress(
            user_id=user.id,
            course_id=course.id,
            org_id=org_id,
            status="in_progress",
            completion_percentage=0,
            enrolled_version=1,
        )
    )
    db.flush()


def _quiz_settings() -> dict:
    return {
        "passing_score": 70,
        "max_attempts": 0,
        "questions": [
            {
                "id": "q1",
                "text": "2+2?",
                "points": 5,
                "options": [{"id": "a", "text": "3"}, {"id": "b", "text": "4"}],
                "correct_option_id": "b",
            },
            {
                "id": "q2",
                "text": "3+3?",
                "points": 15,
                "options": [{"id": "c", "text": "5"}, {"id": "d", "text": "6"}],
                "correct_option_id": "d",
            },
        ],
    }


def test_native_quiz_submit_writes_grade_result_with_runtime_points(client: TestClient, db_session: Session):
    learner = _user(db_session, "learner")
    course, _, block = _course_with_block(db_session, block_type="quiz", settings=_quiz_settings())
    _enroll(db_session, learner, course)
    db_session.commit()

    token = create_access_token(payload={"sub": learner.id, "org_id": ORG_ID})
    response = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "b", "q2": "c"}},
    )

    assert response.status_code == 200
    assert response.json()["score"] == 25

    item = db_session.query(GradeItem).filter_by(org_id=ORG_ID, course_id=course.id, source_type="quiz_block", source_id=str(block.id)).one()
    result = db_session.query(GradeResult).filter_by(org_id=ORG_ID, grade_item_id=item.id, user_id=learner.id).one()
    assert item.points_possible == 20
    assert result.course_version_id == "1"
    assert result.points_awarded == 5
    assert result.points_possible == 20
    assert result.percentage == 25
    assert result.source_type == "quiz_submission"
    assert result.is_current is True


def test_native_quiz_best_attempt_keeps_higher_current_result(client: TestClient, db_session: Session):
    learner = _user(db_session, "learner")
    course, _, block = _course_with_block(db_session, block_type="quiz", settings=_quiz_settings())
    _enroll(db_session, learner, course)
    db_session.commit()

    token = create_access_token(payload={"sub": learner.id, "org_id": ORG_ID})
    first = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "b", "q2": "d"}},
    )
    second = client.post(
        f"/api/v1/learner/blocks/{block.id}/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"answers": {"q1": "a", "q2": "c"}},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    item = db_session.query(GradeItem).filter_by(org_id=ORG_ID, course_id=course.id, source_type="quiz_block", source_id=str(block.id)).one()
    result = db_session.query(GradeResult).filter_by(org_id=ORG_ID, grade_item_id=item.id, user_id=learner.id).one()
    assert result.percentage == 100
    assert result.attempt_number == 1
    assert result.metadata_json["latest_ignored_attempt"]["attempt_number"] == 2


def test_assignment_grade_writes_and_regrade_overwrites_current_result(db_session: Session):
    learner = _user(db_session, "learner")
    admin = _user(db_session, "category_admin")
    course, _, block = _course_with_block(
        db_session,
        block_type="assignment",
        settings={"title": "Lab Report", "points_possible": 100},
    )
    _enroll(db_session, learner, course)
    submission = AssignmentSubmission(
        block_id=block.id,
        user_id=learner.id,
        org_id=ORG_ID,
        submission_text="My report",
        submission_files_json=[],
        attempt_number=1,
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(submission)
    db_session.commit()

    actor = TokenData(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        full_name=admin.full_name,
        role="category_admin",
        org_id=ORG_ID,
        category_scope="academics",
    )
    service = AssignmentService(db_session)
    first = service.grade(submission.id, actor, grade=70, feedback="Good", returned=False)
    first_result = db_session.query(GradeResult).filter_by(org_id=ORG_ID, user_id=learner.id).one()

    second = service.grade(submission.id, actor, grade=85, feedback="Updated", returned=False)
    second_result = db_session.query(GradeResult).filter_by(org_id=ORG_ID, user_id=learner.id).one()

    assert first["submission"]["grade"] == 70
    assert second["submission"]["grade"] == 85
    assert first_result.id == second_result.id
    assert second_result.course_version_id == "1"
    assert second_result.source_type == "assignment_submission"
    assert second_result.points_awarded == 85
    assert second_result.points_possible == 100
    assert second_result.percentage == 85
    assert second_result.feedback == "Updated"
