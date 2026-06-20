import pytest
from sqlalchemy import func, select

from app.api.auth import TokenData
from app.db.rls import set_rls_context
from app.models.audit import AuditLog
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.enrollment import EnrollmentRequest
from app.models.organization import Organization
from app.models.user import User
from app.services.enrollment_service import (
    EnrollmentPermissionError,
    EnrollmentService,
    EnrollmentServiceError,
)


def admin_token(user, *, platform=False):
    return TokenData(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        category_scope=user.category_scope,
        org_id=user.org_id,
        is_platform_admin=platform,
        permissions=[],
    )


def seed_org(db, *, org_id, category_slug="backend-development"):
    org = Organization(
        id=org_id,
        name=f"Org {org_id}",
        type="company",
        domain=f"org{org_id}.test",
        slug=f"org-{org_id}",
        status="active",
    )
    super_admin = User(
        id=f"super-admin-{org_id}",
        username=f"super-admin-{org_id}",
        email=f"super-admin-{org_id}@example.com",
        full_name="Super Admin",
        role="super_admin",
        password_hash="hash",
        avatar_initials="SA",
        gradient_start="#111111",
        gradient_end="#222222",
        org_id=org_id,
    )
    category_admin = User(
        id=f"category-admin-{org_id}",
        username=f"category-admin-{org_id}",
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
        name=f"Course {org_id}",
        slug=f"course-{org_id}",
        description="",
        tier="Basic",
        status="published",
        category_slug=category_slug,
        org_id=org_id,
    )
    db.add(org)
    db.flush()
    db.add_all([super_admin, category_admin, course])
    db.commit()
    return {
        "org": org,
        "super_admin": super_admin,
        "category_admin": category_admin,
        "course": course,
    }


def seed_learner(db, *, org_id, email, category_scope="backend-development", user_id="existing-learner"):
    learner = User(
        id=f"{user_id}-{org_id}",
        username=f"{user_id}-{org_id}",
        email=email,
        full_name="Existing Learner",
        role="learner",
        category_scope=category_scope,
        password_hash="hash",
        avatar_initials="EL",
        gradient_start="#111111",
        gradient_end="#222222",
        org_id=org_id,
    )
    db.add(learner)
    db.commit()
    return learner


def count_rows(db, model, **filters):
    stmt = select(func.count()).select_from(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return db.execute(stmt).scalar_one()


def manual_enroll(db, actor, *, email="learner@example.com", course_ids=None):
    set_rls_context(db, actor.org_id)
    return EnrollmentService(db).manual_enroll(
        actor_token=admin_token(actor),
        full_name="Manual Learner",
        email=email,
        course_ids=course_ids or [f"course-{actor.org_id}"],
        enrollment_type="manual",
        note="test",
    )


def test_manual_enrollment_success_creates_user_request_progress_and_audit(db_session):
    context = seed_org(db_session, org_id=1)

    result = manual_enroll(db_session, context["category_admin"])
    db_session.commit()

    assert result.enrolled_course_ids == [context["course"].id]
    assert result.skipped_course_ids == []
    assert count_rows(db_session, User, email="learner@example.com") == 1
    assert count_rows(db_session, EnrollmentRequest, email="learner@example.com", status="approved") == 1
    assert count_rows(db_session, CourseProgress, user_id=result.user.id, course_id=context["course"].id) == 1
    assert count_rows(db_session, AuditLog, action="learner.manual_provisioned") == 1
    assert count_rows(db_session, AuditLog, action="enrollment.manual") == 1


def test_manual_enrollment_reuses_existing_learner(db_session):
    context = seed_org(db_session, org_id=1)
    learner = seed_learner(db_session, org_id=1, email="existing@example.com")

    result = manual_enroll(db_session, context["super_admin"], email=learner.email)
    db_session.commit()

    assert result.user.id == learner.id
    assert count_rows(db_session, User, email=learner.email) == 1
    assert count_rows(db_session, EnrollmentRequest, email=learner.email, status="approved") == 1
    assert count_rows(db_session, CourseProgress, user_id=learner.id, course_id=context["course"].id) == 1
    assert count_rows(db_session, AuditLog, action="learner.manual_provisioned") == 0
    assert count_rows(db_session, AuditLog, action="enrollment.manual") == 1


def test_duplicate_manual_enrollment_skips_existing_progress(db_session):
    context = seed_org(db_session, org_id=1)

    first = manual_enroll(db_session, context["category_admin"])
    db_session.commit()
    second = manual_enroll(db_session, context["category_admin"])
    db_session.commit()

    assert first.enrolled_course_ids == [context["course"].id]
    assert second.enrolled_course_ids == []
    assert second.skipped_course_ids == [context["course"].id]
    assert count_rows(db_session, User, email="learner@example.com") == 1
    assert count_rows(db_session, EnrollmentRequest, email="learner@example.com", status="approved") == 1
    assert count_rows(db_session, CourseProgress, user_id=first.user.id, course_id=context["course"].id) == 1


def test_manual_enrollment_rejects_existing_learner_from_another_org(db_session):
    org_one = seed_org(db_session, org_id=1)
    seed_org(db_session, org_id=2, category_slug="frontend-development")
    seed_learner(
        db_session,
        org_id=2,
        email="cross-tenant@example.com",
        category_scope="frontend-development",
        user_id="cross-tenant-learner",
    )

    with pytest.raises(EnrollmentServiceError):
        manual_enroll(db_session, org_one["super_admin"], email="cross-tenant@example.com")


def test_manual_enrollment_rejects_existing_admin_email(db_session):
    context = seed_org(db_session, org_id=1)

    with pytest.raises(EnrollmentServiceError, match="not a learner"):
        manual_enroll(db_session, context["super_admin"], email=context["category_admin"].email)

    assert count_rows(db_session, CourseProgress, course_id=context["course"].id) == 0


def test_manual_enrollment_rejects_cross_tenant_course(db_session):
    org_one = seed_org(db_session, org_id=1)
    org_two = seed_org(db_session, org_id=2, category_slug="frontend-development")

    with pytest.raises(EnrollmentPermissionError):
        manual_enroll(db_session, org_one["super_admin"], course_ids=[org_two["course"].id])


def test_manual_enrollment_rejects_category_scope_violation(db_session):
    context = seed_org(db_session, org_id=1, category_slug="backend-development")
    other_course = Course(
        id="course-other-category",
        name="Other Category Course",
        slug="course-other-category",
        description="",
        tier="Basic",
        status="published",
        category_slug="frontend-development",
        org_id=1,
    )
    db_session.add(other_course)
    db_session.commit()

    with pytest.raises(EnrollmentPermissionError, match="Category access denied"):
        manual_enroll(db_session, context["category_admin"], course_ids=[other_course.id])

    assert count_rows(db_session, CourseProgress, course_id=other_course.id) == 0
