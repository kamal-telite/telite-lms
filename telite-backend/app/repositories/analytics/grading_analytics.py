"""Grading and gradebook analytics."""

from typing import Any
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, func, select, desc
from sqlalchemy.orm import Session

from app.models.gradebook import CourseGrade, GradeResult, GradeItem, GradeCategory
from app.models.assignment_submission import AssignmentSubmission
from app.models.category import Category
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.user import User
from app.repositories.analytics.utils import round_value


def get_grading_analytics_super_admin(session: Session, org_id: int | None = None) -> dict[str, Any]:
    """Returns organization-wide grading analytics for Super Admin dashboard."""
    
    # Base queries with org filter
    course_grade_stmt = select(CourseGrade)
    grade_result_stmt = select(GradeResult)
    grade_item_stmt = select(GradeItem)
    
    if org_id:
        course_grade_stmt = course_grade_stmt.where(CourseGrade.org_id == org_id)
        grade_result_stmt = grade_result_stmt.where(GradeResult.org_id == org_id)
        grade_item_stmt = grade_item_stmt.where(GradeItem.org_id == org_id)
    
    # Calculate overall statistics
    total_grades = session.execute(
        select(func.count(CourseGrade.id)).where(
            CourseGrade.percentage.isnot(None),
            CourseGrade.status.in_(["calculated", "released"])
        )
    ).scalar() or 0
    
    if org_id:
        total_grades = session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.org_id == org_id,
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
    
    # Average grade
    avg_grade_result = session.execute(
        select(func.avg(CourseGrade.percentage)).where(
            CourseGrade.percentage.isnot(None),
            CourseGrade.status.in_(["calculated", "released"])
        )
    ).scalar()
    
    if org_id:
        avg_grade_result = session.execute(
            select(func.avg(CourseGrade.percentage)).where(
                CourseGrade.org_id == org_id,
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar()
    
    overall_average = round_value(avg_grade_result) if avg_grade_result else 0.0
    
    # Pass rate (grades >= 60%)
    pass_count = session.execute(
        select(func.count(CourseGrade.id)).where(
            CourseGrade.percentage >= 60.0,
            CourseGrade.status.in_(["calculated", "released"])
        )
    ).scalar() or 0
    
    if org_id:
        pass_count = session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.org_id == org_id,
                CourseGrade.percentage >= 60.0,
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
    
    pass_rate = round_value((pass_count / total_grades * 100.0) if total_grades > 0 else 0.0)
    fail_rate = round_value(100.0 - pass_rate) if total_grades > 0 else 0.0
    
    # Total assessments (grade items)
    total_assessments = session.execute(
        select(func.count(GradeItem.id)).where(GradeItem.deleted_at.is_(None))
    ).scalar() or 0
    
    if org_id:
        total_assessments = session.execute(
            select(func.count(GradeItem.id)).where(
                GradeItem.org_id == org_id,
                GradeItem.deleted_at.is_(None)
            )
        ).scalar() or 0
    
    # Total graded learners (unique users with course grades)
    total_graded_learners = session.execute(
        select(func.count(func.distinct(CourseGrade.user_id))).where(
            CourseGrade.percentage.isnot(None),
            CourseGrade.status.in_(["calculated", "released"])
        )
    ).scalar() or 0
    
    if org_id:
        total_graded_learners = session.execute(
            select(func.count(func.distinct(CourseGrade.user_id))).where(
                CourseGrade.org_id == org_id,
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
    
    # Grade distribution
    grade_distribution = [
        {"range": "90-100%", "count": 0, "label": "A"},
        {"range": "80-89%", "count": 0, "label": "B"},
        {"range": "70-79%", "count": 0, "label": "C"},
        {"range": "60-69%", "count": 0, "label": "D"},
        {"range": "0-59%", "count": 0, "label": "F"},
    ]
    
    for i, (min_pct, max_pct) in enumerate([(90, 100), (80, 89), (70, 79), (60, 69), (0, 59)]):
        count_stmt = select(func.count(CourseGrade.id)).where(
            CourseGrade.percentage >= min_pct,
            CourseGrade.percentage <= (max_pct if max_pct < 100 else 100),
            CourseGrade.status.in_(["calculated", "released"])
        )
        if org_id:
            count_stmt = count_stmt.where(CourseGrade.org_id == org_id)
        grade_distribution[i]["count"] = session.execute(count_stmt).scalar() or 0
    
    # Top performing categories (by average grade)
    category_performance = session.execute(
        select(
            GradeCategory.name,
            func.avg(CourseGrade.percentage).label('avg_grade')
        )
        .join(GradeItem, GradeItem.category_id == GradeCategory.id)
        .join(GradeResult, GradeResult.grade_item_id == GradeItem.id)
        .join(CourseGrade, CourseGrade.user_id == GradeResult.user_id)
        .where(
            GradeCategory.deleted_at.is_(None),
            CourseGrade.percentage.isnot(None),
            CourseGrade.status.in_(["calculated", "released"])
        )
        .group_by(GradeCategory.id, GradeCategory.name)
        .order_by(desc('avg_grade'))
        .limit(10)
    ).all()
    
    category_performance_list = [
        {"category": cat.name, "avg_grade": round_value(cat.avg_grade)}
        for cat in category_performance
    ]
    
    return {
        "kpis": {
            "total_grades": total_grades,
            "overall_average": overall_average,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "total_assessments": total_assessments,
            "total_graded_learners": total_graded_learners,
        },
        "grade_distribution": grade_distribution,
        "category_performance": category_performance_list,
    }


def get_grading_analytics_category_admin(
    session: Session,
    category_slug: str,
    org_id: int | None = None,
) -> dict[str, Any]:
    """Returns live category grading analytics for Category Admin dashboard."""
    category_stmt = select(Category).where(Category.slug == category_slug)
    if org_id:
        category_stmt = category_stmt.where(Category.org_id == org_id)
    category = session.execute(category_stmt).scalar_one_or_none()
    if not category:
        return {}

    course_stmt = select(Course).where(Course.category_slug == category_slug, Course.status != "archived")
    if org_id:
        course_stmt = course_stmt.where(Course.org_id == org_id)
    courses = session.execute(course_stmt.order_by(Course.name)).scalars().all()
    course_ids = [course.id for course in courses]
    empty = {
        "average_grade": 0.0,
        "overall_course_average": 0.0,
        "pass_rate": 0.0,
        "fail_rate": 0.0,
        "quiz_average": 0.0,
        "assignment_average": 0.0,
        "total_learners": 0,
        "total_assessments": 0,
        "pending_evaluations": 0,
        "evaluated_assessments": 0,
        "course_grade_distribution": [],
        "grade_distribution": [],
        "course_performance": [],
        "pass_fail": [{"label": "Pass", "value": 0}, {"label": "Fail", "value": 0}],
        "learners_at_risk": [],
        "top_performers": [],
        "lowest_performers": [],
        "learner_grades": [],
        "assessment_details": [],
        "grade_trend": [],
        "grade_summary": {"total_graded": 0, "total_assessments": 0},
        "filters": {"courses": [], "learners": [], "assessment_types": ["quiz", "assignment"], "statuses": [], "grades": []},
    }
    if not course_ids:
        return empty

    learner_stmt = (
        select(User)
        .join(CourseProgress, CourseProgress.user_id == User.id)
        .where(CourseProgress.course_id.in_(course_ids))
    )
    if org_id:
        learner_stmt = learner_stmt.where(User.org_id == org_id, CourseProgress.org_id == org_id)
    learners = session.execute(learner_stmt.distinct().order_by(User.full_name)).scalars().all()
    learners_by_id = {learner.id: learner for learner in learners}

    result_stmt = (
        select(GradeResult, GradeItem, Course, User)
        .join(GradeItem, GradeItem.id == GradeResult.grade_item_id)
        .join(Course, Course.id == GradeResult.course_id)
        .join(User, User.id == GradeResult.user_id)
        .where(
            GradeResult.course_id.in_(course_ids),
            GradeResult.is_current.is_(True),
            GradeResult.status == "graded",
        )
    )
    if org_id:
        result_stmt = result_stmt.where(
            GradeResult.org_id == org_id,
            GradeItem.org_id == org_id,
            Course.org_id == org_id,
            User.org_id == org_id,
        )
    result_rows = session.execute(result_stmt.order_by(Course.name, User.full_name, GradeItem.title)).all()

    pending_stmt = (
        select(AssignmentSubmission, User, Course, GradeItem)
        .join(GradeItem, GradeItem.source_id == func.cast(AssignmentSubmission.block_id, String))
        .join(Course, Course.id == GradeItem.course_id)
        .join(User, User.id == AssignmentSubmission.user_id)
        .where(
            Course.id.in_(course_ids),
            GradeItem.source_type == "assignment_block",
            AssignmentSubmission.status.in_(["submitted", "resubmitted", "pending_verification", "approved", "rejected"]),
        )
    )
    if org_id:
        pending_stmt = pending_stmt.where(
            AssignmentSubmission.org_id == org_id,
            GradeItem.org_id == org_id,
            Course.org_id == org_id,
            User.org_id == org_id,
        )
    pending_rows = session.execute(pending_stmt).all()

    progress_rows = session.execute(
        select(CourseProgress).where(
            CourseProgress.course_id.in_(course_ids),
            CourseProgress.user_id.in_(list(learners_by_id.keys()) or [""]),
        )
    ).scalars().all()
    completion_by_user_course = {(row.user_id, row.course_id): round_value(row.completion_percentage) for row in progress_rows}

    grade_values: list[float] = []
    quiz_values: list[float] = []
    assignment_values: list[float] = []
    by_learner_course: dict[tuple[str, str], dict[str, Any]] = {}
    assessment_details: list[dict[str, Any]] = []

    def letter_grade(percentage: float | None) -> str:
        value = float(percentage or 0)
        if value >= 90:
            return "A"
        if value >= 80:
            return "B"
        if value >= 70:
            return "C"
        if value >= 60:
            return "D"
        return "F"

    def iso(value: Any) -> str | None:
        return value.isoformat() if hasattr(value, "isoformat") else None

    for result, item, course, learner in result_rows:
        pct = round_value(result.percentage)
        grade_values.append(pct)
        assessment_type = "quiz" if "quiz" in (item.source_type or result.source_type) else "assignment"
        if assessment_type == "quiz":
            quiz_values.append(pct)
        else:
            assignment_values.append(pct)
        key = (learner.id, course.id)
        row = by_learner_course.setdefault(key, {
            "learner_id": learner.id,
            "learner_name": learner.full_name,
            "email": learner.email,
            "course_id": course.id,
            "course": course.name,
            "quiz_scores": [],
            "assignment_scores": [],
            "completed_assessments": 0,
            "pending_assessments": 0,
            "pal_score": round_value(getattr(learner, "pal_score", None)),
        })
        row[f"{assessment_type}_scores"].append(pct)
        row["completed_assessments"] += 1
        evaluator = "System" if result.graded_by == "system" else None
        if result.graded_by and result.graded_by != "system":
            evaluator_user = session.get(User, result.graded_by)
            evaluator = evaluator_user.full_name if evaluator_user else result.graded_by
        assessment_details.append({
            "learner_id": learner.id,
            "learner_name": learner.full_name,
            "email": learner.email,
            "course_id": course.id,
            "course": course.name,
            "quiz_name": item.title if assessment_type == "quiz" else "",
            "assignment_name": item.title if assessment_type == "assignment" else "",
            "assessment_name": item.title,
            "assessment_type": assessment_type,
            "marks_obtained": round_value(result.points_awarded),
            "maximum_marks": round_value(result.points_possible),
            "percentage": pct,
            "grade": letter_grade(pct),
            "status": "approved" if result.status == "graded" else result.status,
            "submission_date": iso(result.created_at),
            "evaluation_date": iso(result.graded_at),
            "evaluator": evaluator or "-",
        })

    for submission, learner, course, item in pending_rows:
        key = (learner.id, course.id)
        row = by_learner_course.setdefault(key, {
            "learner_id": learner.id,
            "learner_name": learner.full_name,
            "email": learner.email,
            "course_id": course.id,
            "course": course.name,
            "quiz_scores": [],
            "assignment_scores": [],
            "completed_assessments": 0,
            "pending_assessments": 0,
            "pal_score": round_value(getattr(learner, "pal_score", None)),
        })
        row["pending_assessments"] += 1
        assessment_details.append({
            "learner_id": learner.id,
            "learner_name": learner.full_name,
            "email": learner.email,
            "course_id": course.id,
            "course": course.name,
            "quiz_name": "",
            "assignment_name": item.title,
            "assessment_name": item.title,
            "assessment_type": "assignment",
            "marks_obtained": None,
            "maximum_marks": round_value(item.points_possible),
            "percentage": None,
            "grade": "-",
            "status": submission.status,
            "submission_date": iso(submission.submitted_at),
            "evaluation_date": iso(submission.graded_at or submission.reviewed_at),
            "evaluator": "-",
        })

    learner_grades = []
    for row in by_learner_course.values():
        quiz_avg = round_value(sum(row["quiz_scores"]) / len(row["quiz_scores"])) if row["quiz_scores"] else 0.0
        assignment_avg = round_value(sum(row["assignment_scores"]) / len(row["assignment_scores"])) if row["assignment_scores"] else 0.0
        all_scores = row["quiz_scores"] + row["assignment_scores"]
        overall = round_value(sum(all_scores) / len(all_scores)) if all_scores else 0.0
        completed = row["completed_assessments"]
        pending = row["pending_assessments"]
        learner_grades.append({
            "learner_id": row["learner_id"],
            "learner_name": row["learner_name"],
            "email": row["email"],
            "course_id": row["course_id"],
            "course": row["course"],
            "quiz_average": quiz_avg,
            "assignment_average": assignment_avg,
            "overall_grade": letter_grade(overall) if completed else "-",
            "overall_percentage": overall,
            "completed_assessments": completed,
            "pending_assessments": pending,
            "pal_score": row["pal_score"],
            "certificate_eligible": "Yes" if overall >= 60 and pending == 0 and completion_by_user_course.get((row["learner_id"], row["course_id"]), 0) >= 100 else "No",
        })

    overall_average = round_value(sum(grade_values) / len(grade_values)) if grade_values else 0.0
    passed = len([row for row in learner_grades if row["completed_assessments"] and row["overall_percentage"] >= 60])
    failed = len([row for row in learner_grades if row["completed_assessments"] and row["overall_percentage"] < 60])
    total_final = passed + failed
    buckets = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for value in grade_values:
        buckets[letter_grade(value)] += 1

    course_performance = []
    for course in courses:
        values = [row["overall_percentage"] for row in learner_grades if row["course_id"] == course.id and row["completed_assessments"]]
        course_performance.append({"course_name": course.name, "average": round_value(sum(values) / len(values)) if values else 0.0})

    top = sorted([row for row in learner_grades if row["completed_assessments"]], key=lambda row: row["overall_percentage"], reverse=True)[:10]
    low = sorted([row for row in learner_grades if row["completed_assessments"]], key=lambda row: row["overall_percentage"])[:10]
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    trend = []
    for idx in range(5, -1, -1):
        start = (month_start - timedelta(days=idx * 31)).replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1)
        values = [round_value(result.percentage) for result, _, _, _ in result_rows if result.graded_at and start <= result.graded_at < end]
        trend.append({"month": start.strftime("%b"), "average": round_value(sum(values) / len(values)) if values else 0.0})

    statuses = sorted({row["status"] for row in assessment_details if row["status"]})
    return {
        "average_grade": overall_average,
        "overall_course_average": overall_average,
        "pass_rate": round_value(passed / total_final * 100.0) if total_final else 0.0,
        "fail_rate": round_value(failed / total_final * 100.0) if total_final else 0.0,
        "quiz_average": round_value(sum(quiz_values) / len(quiz_values)) if quiz_values else 0.0,
        "assignment_average": round_value(sum(assignment_values) / len(assignment_values)) if assignment_values else 0.0,
        "total_learners": len(learners),
        "total_assessments": len(result_rows) + len(pending_rows),
        "pending_evaluations": len(pending_rows),
        "evaluated_assessments": len(result_rows),
        "course_grade_distribution": course_performance,
        "grade_distribution": [{"grade": key, "count": value} for key, value in buckets.items()],
        "course_performance": course_performance,
        "pass_fail": [{"label": "Pass", "value": passed}, {"label": "Fail", "value": failed}],
        "learners_at_risk": [{"full_name": row["learner_name"], "grade": row["overall_percentage"]} for row in low if row["overall_percentage"] < 60],
        "top_performers": [{"full_name": row["learner_name"], "grade": row["overall_percentage"]} for row in top],
        "lowest_performers": [{"full_name": row["learner_name"], "grade": row["overall_percentage"]} for row in low],
        "learner_grades": learner_grades,
        "assessment_details": assessment_details,
        "grade_trend": trend,
        "grade_summary": {"total_graded": len(result_rows), "total_assessments": len(result_rows) + len(pending_rows)},
        "filters": {
            "courses": [{"id": course.id, "name": course.name} for course in courses],
            "learners": [{"id": learner.id, "name": learner.full_name, "email": learner.email} for learner in learners],
            "assessment_types": ["quiz", "assignment"],
            "statuses": statuses,
            "grades": ["A", "B", "C", "D", "F"],
        },
    }


def get_grading_analytics_learner(session: Session, user_id: str) -> dict[str, Any]:
    """Returns learner-specific grading analytics for Learner dashboard."""
    learner = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    org_id = learner.org_id if learner else None
    result_stmt = (
        select(GradeResult, GradeItem, Course)
        .join(GradeItem, GradeItem.id == GradeResult.grade_item_id)
        .join(Course, Course.id == GradeResult.course_id)
        .where(
            GradeResult.user_id == user_id,
            GradeResult.is_current.is_(True),
            GradeResult.percentage.isnot(None),
        )
        .order_by(GradeResult.graded_at.desc().nullslast(), GradeResult.created_at.desc())
    )
    if org_id:
        result_stmt = result_stmt.where(GradeResult.org_id == org_id)
    rows = session.execute(result_stmt).all()
    if not rows:
        return {"has_grades": False, "message": "Grade will be available after evaluation."}

    def letter_grade(percentage: float | int | None) -> str:
        score = float(percentage or 0)
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    assessments = []
    percentages = []
    for result, item, course in rows:
        percentage = round_value(result.percentage)
        percentages.append(percentage)
        assessment_type = "Assignment" if "assignment" in (result.source_type or "") else "Quiz" if "quiz" in (result.source_type or "") else "Assessment"
        assessments.append({
            "id": result.id,
            "course_id": course.id,
            "course_name": course.name,
            "assessment_name": item.title,
            "quiz_name": item.title if assessment_type == "Quiz" else None,
            "assignment_name": item.title if assessment_type == "Assignment" else None,
            "assessment_type": assessment_type,
            "source_type": result.source_type,
            "source_id": result.source_id,
            "attempt_number": result.attempt_number,
            "attempts_used": result.attempt_number,
            "marks_obtained": round_value(result.points_awarded),
            "maximum_marks": round_value(result.points_possible),
            "percentage": percentage,
            "grade": letter_grade(percentage),
            "passed": percentage >= 60,
            "pass_fail": "Pass" if percentage >= 60 else "Fail",
            "submission_date": result.created_at.isoformat() if result.created_at else None,
            "evaluation_date": result.graded_at.isoformat() if result.graded_at else None,
            "feedback": result.feedback,
            "status": result.status,
        })

    overall_average = round_value(sum(percentages) / len(percentages))
    quiz_rows = [row for row in assessments if row["assessment_type"] == "Quiz"]
    assignment_rows = [row for row in assessments if row["assessment_type"] == "Assignment"]
    grade_summary = []
    for course_id in sorted({row["course_id"] for row in assessments}):
        course_assessments = [row for row in assessments if row["course_id"] == course_id]
        course_average = round_value(sum(float(row["percentage"]) for row in course_assessments) / len(course_assessments))
        grade_summary.append({
            "course_name": course_assessments[0]["course_name"],
            "completion_percentage": 0.0,
            "average_quiz_score": round_value(sum(float(row["percentage"]) for row in course_assessments if row["assessment_type"] == "Quiz") / len([row for row in course_assessments if row["assessment_type"] == "Quiz"])) if any(row["assessment_type"] == "Quiz" for row in course_assessments) else 0.0,
            "average_assignment_score": round_value(sum(float(row["percentage"]) for row in course_assessments if row["assessment_type"] == "Assignment") / len([row for row in course_assessments if row["assessment_type"] == "Assignment"])) if any(row["assessment_type"] == "Assignment" for row in course_assessments) else 0.0,
            "percentage": course_average,
            "overall_course_grade": course_average,
            "display_grade": letter_grade(course_average),
            "passed": course_average >= 60,
            "status": "calculated",
            "certificate_eligibility": False,
        })

    return {
        "has_grades": True,
        "final_grade": overall_average,
        "overall_grade": letter_grade(overall_average),
        "current_percentage": overall_average,
        "quiz_average": round_value(sum(float(row["percentage"]) for row in quiz_rows) / len(quiz_rows)) if quiz_rows else 0.0,
        "assignment_average": round_value(sum(float(row["percentage"]) for row in assignment_rows) / len(assignment_rows)) if assignment_rows else 0.0,
        "pass_fail_status": "Pass" if overall_average >= 60 else "Fail",
        "completed_assessments": len(assessments),
        "pending_evaluations": 0,
        "highest_score": round_value(max(percentages)),
        "lowest_score": round_value(min(percentages)),
        "assessments": assessments,
        "grade_summary": grade_summary,
        "grade_progress": [{"course_name": row["course_name"], "percentage": row["percentage"]} for row in grade_summary],
        "total_courses_graded": len(grade_summary),
    }
