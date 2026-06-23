from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.gradebook import CourseGrade, GradeCategory, GradeItem, GradeResult, GradingScheme
from app.models.organization import Organization
from app.models.user import User
from app.services.grade_aggregation_service import GradeAggregationService


ORG_ID = 7201


def _seed_base(db: Session):
    org = Organization(
        id=ORG_ID,
        name="Grade Aggregation Org",
        type="company",
        domain="grade-aggregation.example.edu",
        slug="grade-aggregation",
        status="active",
        plan="pro",
    )
    db.add(org)
    db.flush()
    user = User(
        id=f"learner-{uuid.uuid4().hex[:8]}",
        username=f"learner-{uuid.uuid4().hex[:8]}",
        email=f"learner-{uuid.uuid4().hex[:8]}@example.edu",
        full_name="Learner",
        role="learner",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="LR",
        gradient_start="#111111",
        gradient_end="#222222",
    )
    admin = User(
        id=f"admin-{uuid.uuid4().hex[:8]}",
        username=f"admin-{uuid.uuid4().hex[:8]}",
        email=f"admin-{uuid.uuid4().hex[:8]}@example.edu",
        full_name="Admin",
        role="super_admin",
        org_id=ORG_ID,
        organization_id=ORG_ID,
        password_hash="not-used",
        avatar_initials="AD",
        gradient_start="#333333",
        gradient_end="#444444",
    )
    course = Course(
        id=f"course-{uuid.uuid4().hex[:8]}",
        name="Aggregation Course",
        slug=f"aggregation-course-{uuid.uuid4().hex[:8]}",
        category_slug="academics",
        status="published",
        org_id=ORG_ID,
    )
    db.add_all([user, admin, course])
    db.flush()
    return user, admin, course


def _scheme(db: Session, admin: User, *, threshold: float = 70, scheme_type: str = "percentage", scale=None, rounding="nearest"):
    scheme = GradingScheme(
        org_id=ORG_ID,
        name="Default Scheme",
        scheme_type=scheme_type,
        scale_json=scale or {},
        default_pass_threshold=threshold,
        rounding_mode=rounding,
        is_org_default=True,
        created_by=admin.id,
    )
    db.add(scheme)
    db.flush()
    return scheme


def _item(db: Session, admin: User, course: Course, *, source_id: str, points=100, category_id=None, required=True):
    item = GradeItem(
        org_id=ORG_ID,
        course_id=course.id,
        category_id=category_id,
        source_type="manual",
        source_id=source_id,
        title=source_id,
        points_possible=points,
        is_required=required,
        is_extra_credit=False,
        is_released=False,
        grading_policy_json={"attempt_strategy": "latest"},
        sort_order=0,
        created_by=admin.id,
    )
    db.add(item)
    db.flush()
    return item


def _result(db: Session, user: User, course: Course, item: GradeItem, *, awarded, possible, version="1", status="graded"):
    result = GradeResult(
        org_id=ORG_ID,
        course_id=course.id,
        course_version_id=version,
        grade_item_id=item.id,
        user_id=user.id,
        source_type="manual_entry",
        source_id=f"source-{item.id}-{version}",
        points_awarded=awarded,
        points_possible=possible,
        percentage=(awarded / possible * 100) if possible else None,
        status=status,
        is_current=True,
        metadata_json={},
    )
    db.add(result)
    db.flush()
    return result


def test_course_grade_points_aggregation_and_pass_fail(db_session: Session):
    user, admin, course = _seed_base(db_session)
    _scheme(db_session, admin, threshold=70)
    item_one = _item(db_session, admin, course, source_id="quiz", points=100)
    item_two = _item(db_session, admin, course, source_id="assignment", points=100)
    _result(db_session, user, course, item_one, awarded=80, possible=100)
    _result(db_session, user, course, item_two, awarded=90, possible=100)

    grade = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
    )

    assert grade.status == "calculated"
    assert grade.percentage == 85
    assert grade.display_grade == "85.00%"
    assert grade.passed is True
    assert grade.metadata_json["aggregation_strategy"] == "points"


def test_course_grade_category_weighting(db_session: Session):
    user, admin, course = _seed_base(db_session)
    _scheme(db_session, admin, threshold=60)
    quizzes = GradeCategory(org_id=ORG_ID, course_id=course.id, name="Quizzes", weight=40, created_by=admin.id)
    assignments = GradeCategory(org_id=ORG_ID, course_id=course.id, name="Assignments", weight=60, created_by=admin.id)
    db_session.add_all([quizzes, assignments])
    db_session.flush()
    quiz = _item(db_session, admin, course, source_id="quiz", points=100, category_id=quizzes.id)
    assignment = _item(db_session, admin, course, source_id="assignment", points=100, category_id=assignments.id)
    _result(db_session, user, course, quiz, awarded=80, possible=100)
    _result(db_session, user, course, assignment, awarded=90, possible=100)

    grade = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
    )

    assert grade.percentage == 86
    assert grade.passed is True
    assert grade.metadata_json["aggregation_strategy"] == "category_weighted"
    assert len(grade.metadata_json["category_breakdown"]) == 2


def test_missing_required_item_keeps_course_grade_draft(db_session: Session):
    user, admin, course = _seed_base(db_session)
    _scheme(db_session, admin, threshold=60)
    graded_item = _item(db_session, admin, course, source_id="quiz", points=100)
    missing_item = _item(db_session, admin, course, source_id="assignment", points=100, required=True)
    _result(db_session, user, course, graded_item, awarded=90, possible=100)

    grade = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
    )

    assert grade.status == "draft"
    assert grade.passed is None
    assert missing_item.id in grade.metadata_json["missing_grade_item_ids"]
    assert grade.metadata_json["has_missing_required_items"] is True


def test_course_grade_aggregation_is_version_aware(db_session: Session):
    user, admin, course = _seed_base(db_session)
    _scheme(db_session, admin, threshold=60)
    item = _item(db_session, admin, course, source_id="quiz", points=100)
    _result(db_session, user, course, item, awarded=40, possible=100, version="1")
    _result(db_session, user, course, item, awarded=95, possible=100, version="2")

    grade_v1 = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
    )
    grade_v2 = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="2",
    )

    assert grade_v1.percentage == 40
    assert grade_v1.passed is False
    assert grade_v2.percentage == 95
    assert grade_v2.passed is True


def test_locked_course_grade_is_not_recalculated(db_session: Session):
    user, admin, course = _seed_base(db_session)
    _scheme(db_session, admin, threshold=60)
    item = _item(db_session, admin, course, source_id="quiz", points=100)
    _result(db_session, user, course, item, awarded=50, possible=100)
    locked = CourseGrade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
        percentage=77,
        display_grade="77.00%",
        passed=True,
        status="locked",
        metadata_json={"locked": True},
    )
    db_session.add(locked)
    db_session.flush()

    grade = GradeAggregationService(db_session).recalculate_course_grade(
        org_id=ORG_ID,
        course_id=course.id,
        user_id=user.id,
        course_version_id="1",
    )

    assert grade.id == locked.id
    assert grade.percentage == 77
    assert grade.status == "locked"
