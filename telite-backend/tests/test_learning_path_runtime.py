from __future__ import annotations

from datetime import datetime, timezone

from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.gradebook import CompletionRule, CourseGrade
from app.models.learner_event import LearnerEvent
from app.models.learning_path import LearningPath, LearningPathCourse
from app.models.organization import Organization
from app.models.user import User
from app.repositories.learner_repo import LearnerRepository
from app.repositories.learning_path_progress_repo import LearningPathProgressRepository
from app.services.learning_path_unlock_service import LearningPathUnlockService


ORG_ID = 61
OTHER_ORG_ID = 62
LEARNER_ID = "learner-lp-1"
OTHER_LEARNER_ID = "learner-lp-2"


def _seed_learning_path(db_session) -> LearningPath:
    org = Organization(
        id=ORG_ID,
        name="Learning Path Org",
        type="company",
        domain="lp.example.edu",
        slug="learning-path-org",
        status="active",
        plan="free",
    )
    other_org = Organization(
        id=OTHER_ORG_ID,
        name="Other Learning Path Org",
        type="company",
        domain="lp-other.example.edu",
        slug="learning-path-other-org",
        status="active",
        plan="free",
    )
    learner = User(
        id=LEARNER_ID,
        username="learner-lp-1",
        email="learner-lp-1@example.edu",
        full_name="Learning Path Learner",
        role="learner",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="LP",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    other_learner = User(
        id=OTHER_LEARNER_ID,
        username="learner-lp-2",
        email="learner-lp-2@example.edu",
        full_name="Unassigned Learner",
        role="learner",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="UL",
        gradient_start="#333333",
        gradient_end="#444444",
    )
    cross_tenant_learner = User(
        id="learner-lp-cross",
        username="learner-lp-cross",
        email="learner-lp-cross@example.edu",
        full_name="Cross Tenant Learner",
        role="learner",
        org_id=OTHER_ORG_ID,
        organization_id=OTHER_ORG_ID,
        password_hash="not-used",
        avatar_initials="CT",
        gradient_start="#555555",
        gradient_end="#666666",
    )
    courses = [
        Course(
            id="lp-course-1",
            org_id=ORG_ID,
            category_slug="learning-path-org",
            name="Learning Path Course 1",
            slug="learning-path-course-1",
            description="First course",
            status="active",
        ),
        Course(
            id="lp-course-2",
            org_id=ORG_ID,
            category_slug="learning-path-org",
            name="Learning Path Course 2",
            slug="learning-path-course-2",
            description="Second course",
            status="active",
        ),
    ]
    path = LearningPath(
        id=6101,
        org_id=ORG_ID,
        title="Runtime Path",
        description="Runtime hardening path",
        settings="{}",
    )
    other_path = LearningPath(
        id=6201,
        org_id=OTHER_ORG_ID,
        title="Other Runtime Path",
        description="Cross tenant path",
        settings="{}",
    )
    db_session.add_all([org, other_org])
    db_session.commit()
    db_session.add_all([learner, other_learner, cross_tenant_learner, *courses, path, other_path])
    db_session.flush()
    db_session.add_all(
        [
            LearningPathCourse(path_id=path.id, course_id="lp-course-1", org_id=ORG_ID, sort_order=1),
            LearningPathCourse(path_id=path.id, course_id="lp-course-2", org_id=ORG_ID, sort_order=2),
        ]
    )
    db_session.commit()
    return path


def _complete_course(db_session, course_id: str) -> CourseProgress:
    progress = CourseProgress(
        user_id=LEARNER_ID,
        course_id=course_id,
        org_id=ORG_ID,
        status="completed",
        completion_percentage=100.0,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(progress)
    db_session.commit()
    return progress


def _pending_grade_course(db_session, course_id: str) -> CourseProgress:
    progress = CourseProgress(
        user_id=LEARNER_ID,
        course_id=course_id,
        org_id=ORG_ID,
        status="pending_grade",
        completion_percentage=100.0,
        enrolled_version=1,
    )
    db_session.add(progress)
    db_session.commit()
    return progress


def _grade_rule(db_session, course_id: str) -> CompletionRule:
    rule = CompletionRule(
        org_id=ORG_ID,
        course_id=course_id,
        requires_content_completion=True,
        minimum_content_percentage=100,
        requires_grade_pass=True,
        minimum_final_percentage=60,
        requires_instructor_approval=False,
        certificate_eligible_on_completion=True,
        status="active",
        rule_json={},
    )
    db_session.add(rule)
    db_session.flush()
    return rule


def _course_grade(db_session, course_id: str, *, passed: bool = True, percentage: float = 85) -> CourseGrade:
    grade = CourseGrade(
        org_id=ORG_ID,
        course_id=course_id,
        course_version_id="1",
        user_id=LEARNER_ID,
        percentage=percentage,
        display_grade=f"{percentage:.2f}%",
        passed=passed,
        status="calculated",
        metadata_json={},
    )
    db_session.add(grade)
    db_session.flush()
    return grade


def _unlock_events(db_session):
    return (
        db_session.query(LearnerEvent)
        .filter(
            LearnerEvent.user_id == LEARNER_ID,
            LearnerEvent.org_id == ORG_ID,
            LearnerEvent.event_type == "COURSE_UNLOCKED",
        )
        .order_by(LearnerEvent.id)
        .all()
    )


def test_learning_path_assignment_boundary_is_idempotent(db_session):
    path = _seed_learning_path(db_session)
    repo = LearningPathProgressRepository(db_session)

    progress, created = repo.assign_path(LEARNER_ID, path.id, ORG_ID)
    duplicate, duplicate_created = repo.assign_path(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert created is True
    assert duplicate_created is False
    assert duplicate.id == progress.id
    assert duplicate.status == "not_started"
    assert (
        db_session.query(type(progress))
        .filter_by(user_id=LEARNER_ID, path_id=path.id, org_id=ORG_ID)
        .count()
        == 1
    )


def test_learning_path_unlock_sequence_and_deduplication(db_session):
    path = _seed_learning_path(db_session)
    LearningPathProgressRepository(db_session).assign_path(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    service = LearningPathUnlockService(db_session)

    first_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    duplicate_first = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert first_unlock is not None
    assert first_unlock.course_id == "lp-course-1"
    assert duplicate_first is None
    assert [event.course_id for event in _unlock_events(db_session)] == ["lp-course-1"]

    _complete_course(db_session, "lp-course-1")
    second_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    duplicate_second = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert second_unlock is not None
    assert second_unlock.course_id == "lp-course-2"
    assert duplicate_second is None
    assert [event.course_id for event in _unlock_events(db_session)] == ["lp-course-1", "lp-course-2"]
    assert _unlock_events(db_session)[1].payload_json == {
        "path_id": path.id,
        "course_id": "lp-course-2",
        "step": 2,
    }


def test_learning_path_learner_access_isolation(db_session):
    path = _seed_learning_path(db_session)
    progress_repo = LearningPathProgressRepository(db_session)
    progress_repo.assign_path(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    learner_repo = LearnerRepository(db_session)

    assigned_paths = learner_repo.get_learning_paths(LEARNER_ID, ORG_ID)
    assert [item.id for item in assigned_paths] == [path.id]
    assert learner_repo.get_learning_path(path.id, LEARNER_ID, ORG_ID).id == path.id

    assert learner_repo.get_learning_paths(OTHER_LEARNER_ID, ORG_ID) == []
    assert learner_repo.get_learning_path(path.id, OTHER_LEARNER_ID, ORG_ID) is None
    assert learner_repo.get_learning_paths("learner-lp-cross", OTHER_ORG_ID) == []
    assert learner_repo.get_learning_path(path.id, "learner-lp-cross", OTHER_ORG_ID) is None

    path.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    assert learner_repo.get_learning_paths(LEARNER_ID, ORG_ID) == []
    assert learner_repo.get_learning_path(path.id, LEARNER_ID, ORG_ID) is None


def test_learning_path_completion_transition_is_idempotent(db_session):
    path = _seed_learning_path(db_session)
    progress_repo = LearningPathProgressRepository(db_session)
    progress, _ = progress_repo.assign_path(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    service = LearningPathUnlockService(db_session)

    _complete_course(db_session, "lp-course-1")
    partial_progress, completed_now = service.evaluate_completion(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert partial_progress.id == progress.id
    assert completed_now is False
    assert partial_progress.status == "in_progress"
    assert partial_progress.completion_percentage == 50.0

    _complete_course(db_session, "lp-course-2")
    completed_progress, completed_now = service.evaluate_completion(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    repeated_progress, repeated_completed_now = service.evaluate_completion(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert completed_now is True
    assert completed_progress.status == "completed"
    assert completed_progress.completion_percentage == 100.0
    assert completed_progress.completed_at is not None
    assert repeated_progress.id == completed_progress.id
    assert repeated_completed_now is False
    assert (
        db_session.query(type(completed_progress))
        .filter_by(user_id=LEARNER_ID, path_id=path.id, org_id=ORG_ID, status="completed")
        .count()
        == 1
    )


def test_learning_path_does_not_unlock_next_course_for_pending_grade(db_session):
    path = _seed_learning_path(db_session)
    LearningPathProgressRepository(db_session).assign_path(LEARNER_ID, path.id, ORG_ID)
    _grade_rule(db_session, "lp-course-1")
    db_session.commit()
    service = LearningPathUnlockService(db_session)

    first_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    assert first_unlock is not None
    assert first_unlock.course_id == "lp-course-1"

    _pending_grade_course(db_session, "lp-course-1")
    second_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert second_unlock is None
    assert [event.course_id for event in _unlock_events(db_session)] == ["lp-course-1"]


def test_learning_path_unlocks_next_course_for_grade_aware_completed_course(db_session):
    path = _seed_learning_path(db_session)
    LearningPathProgressRepository(db_session).assign_path(LEARNER_ID, path.id, ORG_ID)
    _grade_rule(db_session, "lp-course-1")
    db_session.commit()
    service = LearningPathUnlockService(db_session)

    first_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()
    assert first_unlock is not None
    assert first_unlock.course_id == "lp-course-1"

    _complete_course(db_session, "lp-course-1").enrolled_version = 1
    _course_grade(db_session, "lp-course-1", passed=True, percentage=92)
    db_session.commit()

    second_unlock = service.evaluate_unlocks(LEARNER_ID, path.id, ORG_ID)
    db_session.commit()

    assert second_unlock is not None
    assert second_unlock.course_id == "lp-course-2"
    assert [event.course_id for event in _unlock_events(db_session)] == ["lp-course-1", "lp-course-2"]
