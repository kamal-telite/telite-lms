import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.auth import TokenData
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.enrollment import EnrollmentRequest
from app.models.lesson_block import LessonBlock
from app.models.organization import Organization
from app.models.user import User
from app.services.assignment_service import AssignmentService, set_assignment_actor_context


class NoopStorage:
    async def upload(self, **_kwargs):
        raise AssertionError("No file uploads expected in this test")

    def resolve(self, _file_path):
        raise AssertionError("No download expected in this test")

    def delete(self, _file_path):
        return None


def token(user_id, *, role="learner", org_id=1, category_scope=None, platform=False):
    return TokenData(
        id=user_id,
        username=f"{user_id}@example.com",
        email=f"{user_id}@example.com",
        full_name=user_id,
        role=role,
        category_scope=category_scope,
        org_id=org_id,
        is_platform_admin=platform,
    )


def seed_assignment_context(db, *, org_id=1, category_slug="backend-development"):
    org = Organization(
        id=org_id,
        name=f"Org {org_id}",
        type="company",
        domain=f"org{org_id}.test",
        slug=f"org-{org_id}",
        status="active",
    )
    learner = User(
        id=f"learner-{org_id}",
        username=f"learner-{org_id}@example.com",
        email=f"learner-{org_id}@example.com",
        full_name="Learner",
        role="learner",
        password_hash="hash",
        avatar_initials="LR",
        gradient_start="#111111",
        gradient_end="#222222",
        org_id=org_id,
    )
    category_admin = User(
        id=f"category-admin-{org_id}",
        username=f"category-admin-{org_id}@example.com",
        email=f"category-admin-{org_id}@example.com",
        full_name="Category Admin",
        role="category_admin",
        category_scope=category_slug,
        password_hash="hash",
        avatar_initials="CA",
        gradient_start="#111111",
        gradient_end="#222222",
        org_id=org_id,
    )
    course = Course(
        id=f"course-{org_id}",
        name="Native Assignment Course",
        slug=f"native-assignment-course-{org_id}",
        description="",
        category_slug=category_slug,
        status="published",
        org_id=org_id,
    )
    module = CourseModule(
        course_id=course.id,
        title="Assignment Module",
        module_type="assignment",
        status="published",
        org_id=org_id,
    )
    db.add(org)
    db.flush()
    db.add_all([learner, category_admin, course])
    db.flush()
    db.add(module)
    db.flush()
    block = LessonBlock(
        module_id=module.id,
        org_id=org_id,
        block_type="assignment",
        content="Submit your work",
        metadata_json={"title": "Submit your work"},
    )
    enrollment = EnrollmentRequest(
        id=f"enrollment-{org_id}",
        full_name=learner.full_name,
        email=learner.email,
        category_slug=category_slug,
        request_type="course",
        org_id=org_id,
        status="approved",
        requested_at="2026-06-20T00:00:00",
    )
    db.add_all([block, enrollment])
    db.flush()
    return {
        "org": org,
        "learner": learner,
        "category_admin": category_admin,
        "course": course,
        "module": module,
        "block": block,
    }


def test_assignment_submit_requires_enrollment(db_session):
    context = seed_assignment_context(db_session)
    db_session.commit()
    learner = token(context["learner"].id, org_id=context["org"].id)

    service = AssignmentService(db_session, storage=NoopStorage())
    result = asyncio.run(service.submit(context["block"].id, learner, "Submitted response", [], resubmit=False))

    assert result["submission"]["status"] == "submitted"
    assert result["submission"]["learner_id"] == learner.id

    db_session.query(EnrollmentRequest).delete()
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.submit(context["block"].id, learner, "Second response", [], resubmit=False))
    assert exc.value.status_code == 403


def test_category_admin_grading_is_category_scoped(db_session):
    context = seed_assignment_context(db_session)
    submission = AssignmentSubmission(
        block_id=context["block"].id,
        user_id=context["learner"].id,
        org_id=context["org"].id,
        submission_text="Ready for review",
        status="submitted",
        attempt_number=1,
    )
    db_session.add(submission)
    db_session.commit()

    service = AssignmentService(db_session, storage=NoopStorage())
    admin = token(
        context["category_admin"].id,
        role="category_admin",
        org_id=context["org"].id,
        category_scope=context["course"].category_slug,
    )

    graded = service.grade(submission.id, admin, grade=92, feedback="Strong work", returned=False)
    assert graded["submission"]["status"] == "graded"
    assert graded["submission"]["grade"] == 92

    wrong_scope = token(
        "wrong-scope-admin",
        role="category_admin",
        org_id=context["org"].id,
        category_scope="another-category",
    )
    with pytest.raises(HTTPException) as exc:
        service.grade(submission.id, wrong_scope, grade=50, feedback="Nope", returned=False)
    assert exc.value.status_code == 403


def test_cross_tenant_assignment_access_is_rejected(db_session):
    org_one = seed_assignment_context(db_session, org_id=1, category_slug="backend-development")
    org_two = seed_assignment_context(db_session, org_id=2, category_slug="frontend-development")
    db_session.commit()

    service = AssignmentService(db_session, storage=NoopStorage())
    org_one_learner = token(org_one["learner"].id, org_id=1)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.submit(org_two["block"].id, org_one_learner, "Cross tenant attempt", [], resubmit=False))
    assert exc.value.status_code == 404


def test_assignment_actor_context_sets_rls_claims(db_session):
    learner = token("learner-1", org_id=42)
    set_assignment_actor_context(db_session, learner)

    org_id, bypass, actor_id, actor_role = db_session.execute(
        text(
            "SELECT current_setting('app.current_org_id', true), "
            "current_setting('app.bypass_rls', true), "
            "current_setting('app.current_user_id', true), "
            "current_setting('app.current_user_role', true)"
        )
    ).one()

    assert org_id == "42"
    assert bypass == "off"
    assert actor_id == "learner-1"
    assert actor_role == "learner"
