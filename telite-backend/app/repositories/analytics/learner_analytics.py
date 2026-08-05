"""Learner-specific analytics queries."""

from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.learner_event import LearnerEvent
from app.models.learning_session import LearningSession
from app.models.assignment_submission import AssignmentSubmission
from app.models.task import Task
from app.models.task_workflow import TaskAssignment
from app.models.enrollment import EnrollmentRequest
from app.services.pal_score_service import PALScoreService
from app.repositories.analytics.utils import (
    round_value,
    safe_json_list,
    iso_format,
)
from app.repositories.analytics.global_analytics import get_cohort_rankings


def calculate_learner_streak(session: Session, user_id: str) -> int:
    """Calculates active learning streak based on consecutive days of activity."""
    events_stmt = select(LearnerEvent.created_at).where(LearnerEvent.user_id == user_id)
    event_dates = {dt.date() for dt in session.execute(events_stmt).scalars().all() if dt}

    sessions_stmt = select(LearningSession.started_at).where(LearningSession.user_id == user_id)
    session_dates = {dt.date() for dt in session.execute(sessions_stmt).scalars().all() if dt}

    all_dates = event_dates.union(session_dates)
    if not all_dates:
        return 0

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    if today in all_dates:
        current_date = today
    elif yesterday in all_dates:
        current_date = yesterday
    else:
        return 0

    streak = 0
    check_date = current_date
    while check_date in all_dates:
        streak += 1
        check_date = check_date - timedelta(days=1)

    return streak


def get_learner_summary(session: Session, user_id: str) -> dict[str, Any]:
    """Provides metrics for Learner Dashboard."""
    user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise ValueError("User not found.")
        
    # Recalculate streak in real-time and update db user column
    calculated_streak = calculate_learner_streak(session, user_id)
    if user.streak_days != calculated_streak:
        user.streak_days = calculated_streak
        session.commit()
    pal_metrics = PALScoreService(session).recompute_user(user.id, user.org_id)
        
    progress = session.execute(
        select(CourseProgress).where(CourseProgress.user_id == user_id)
    ).scalars().all()
    progress_by_course = {row.course_id: row for row in progress}
    legacy_progress = {
        item.get("course_id"): item
        for item in safe_json_list(user.course_progress_json)
        if item.get("course_id")
    }

    course_stmt = select(Course).where(
        Course.org_id == user.org_id,
        Course.status.in_(("active", "published")),
        Course.status != "draft",
    )
    if user.role == "learner" and user.category_scope:
        course_stmt = course_stmt.where(Course.category_slug == user.category_scope)
    courses = list(session.execute(course_stmt.order_by(Course.name)).scalars().all())

    approved_enrollments = session.execute(
        select(EnrollmentRequest.category_slug).where(
            EnrollmentRequest.email == user.email,
            EnrollmentRequest.org_id == user.org_id,
            EnrollmentRequest.status == "approved",
        )
    ).scalars().all()
    approved_categories = {slug for slug in approved_enrollments if slug}
    if approved_categories:
        courses = [
            course for course in courses
            if course.category_slug in approved_categories or course.category_slug == user.category_scope
        ]

    def course_progress_payload(course: Course) -> dict[str, Any]:
        row = progress_by_course.get(course.id)
        legacy = legacy_progress.get(course.id, {})
        if row:
            learner_status = row.status
            completion_pct = round_value(row.completion_percentage, 0)
            time_spent_seconds = row.time_spent_seconds
            last_active = row.last_viewed_at.isoformat() if row.last_viewed_at else None
        else:
            learner_status = legacy.get("status", "not_started")
            completion_pct = round_value(legacy.get("progress", 0), 0)
            time_spent_seconds = 0
            last_active = None
        return {
            "id": course.id,
            "course_id": course.id,
            "name": course.name,
            "description": course.description,
            "slug": course.slug,
            "tier": course.tier,
            "status": learner_status,
            "course_status": course.status,
            "progress": completion_pct,
            "completion_pct": completion_pct,
            "completion_percentage": completion_pct,
            "time_spent_seconds": time_spent_seconds,
            "modules_count": course.module_count,
            "module_count": course.module_count,
            "hours": course.hours,
            "last_active": last_active,
            "cover_image_url": course.cover_image_url,
            "category_slug": course.category_slug,
        }

    course_rows = [course_progress_payload(course) for course in courses]
    course_by_id = {course.id: course for course in courses}
    current_course = None
    if progress:
        latest_progress = max(
            progress,
            key=lambda row: row.last_viewed_at or row.updated_at or row.created_at
        )
        if latest_progress.course_id in course_by_id:
            current_course = course_progress_payload(course_by_id[latest_progress.course_id])
    
    if not current_course and user.current_course_id and user.current_course_id in course_by_id:
        current_course = course_progress_payload(course_by_id[user.current_course_id])
        
    if not current_course and course_rows:
        current_course = course_rows[0]
    
    # Determine stats from events and session ledger
    quiz_submit_stmt = select(func.count(LearnerEvent.id)).where(
        LearnerEvent.user_id == user_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED"
    )
    quizzes_submitted = session.execute(quiz_submit_stmt).scalar() or 0
    
    total_time_seconds = session.execute(
        select(func.sum(LearningSession.active_seconds)).where(
            LearningSession.user_id == user_id,
            LearningSession.org_id == user.org_id,
        )
    ).scalar() or 0
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_time_seconds = session.execute(
        select(func.sum(LearningSession.active_seconds)).where(
            LearningSession.user_id == user_id,
            LearningSession.org_id == user.org_id,
            LearningSession.started_at >= today_start,
        )
    ).scalar() or 0
    last_session = session.execute(
        select(LearningSession)
        .where(
            LearningSession.user_id == user_id,
            LearningSession.org_id == user.org_id
        )
        .order_by(LearningSession.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    latest_assignment = session.execute(
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.org_id == user.org_id
        )
        .order_by(
            AssignmentSubmission.submitted_at.desc().nullslast(),
            AssignmentSubmission.updated_at.desc()
        )
        .limit(1)
    ).scalar_one_or_none()

    # Calculate PAL breakdown from live learner performance
    completed_courses_count = len([p for p in progress if p.status == 'completed'])
    total_courses_count = len(courses) or 1
    completion_pct = pal_metrics["course_completion"]
    
    quiz_avg = pal_metrics["quiz_average"]
    
    task_completion = pal_metrics["task_completion"]

    task_stmt = (
        select(Task, TaskAssignment, User)
        .outerjoin(
            TaskAssignment,
            and_(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.learner_id == user_id,
            ),
        )
        .outerjoin(User, User.id == Task.assigned_by)
        .where(Task.org_id == user.org_id)
        .where(
            or_(
                TaskAssignment.learner_id == user_id,
                Task.assignment_scope == "all",
            )
        )
        .order_by(
            TaskAssignment.updated_at.desc().nullslast(),
            TaskAssignment.assigned_at.desc().nullslast(),
            Task.created_at.desc(),
        )
    )
    accessible_task_categories = {slug for slug in approved_categories if slug}
    if user.category_scope:
        accessible_task_categories.add(user.category_scope)
    if accessible_task_categories:
        task_stmt = task_stmt.where(
            or_(
                Task.category_slug.in_(accessible_task_categories),
                Task.is_cross_category.is_(True),
            )
        )

    task_rows = []
    for task, assignment, assigner in session.execute(task_stmt).all():
        status = assignment.status if assignment else "assigned"
        task_rows.append({
            "id": task.id,
            "assignment_id": assignment.id if assignment else None,
            "title": task.title,
            "description": task.description,
            "instructions": task.notes or task.description or "",
            "assigned_by": task.assigned_by,
            "assigned_by_name": assigner.full_name if assigner else "Category Admin",
            "assigned_label": task.assigned_label,
            "assigned_to_user_id": task.assigned_to_user_id,
            "category_slug": task.category_slug,
            "due_at": task.due_at,
            "status": status,
            "assigned_at": assignment.assigned_at.isoformat() if assignment and assignment.assigned_at else None,
            "started_at": assignment.started_at.isoformat() if assignment and assignment.started_at else None,
            "submitted_at": assignment.submitted_at.isoformat() if assignment and assignment.submitted_at else None,
            "completed_at": assignment.completed_at.isoformat() if assignment and assignment.completed_at else None,
        })

    # Get leaderboard and calculate user's rank
    leaderboard_data = get_cohort_rankings(
        session,
        category_slug=user.category_scope,
        org_id=user.org_id,
        limit=50
    )
    user_rank = None
    for idx, row in enumerate(leaderboard_data):
        if row.get("id") == user_id:
            user_rank = idx + 1
            break

    return {
        "profile": {"full_name": user.full_name, "category_scope": user.category_scope},
        "hero": {
            "headline": f"Good morning, {user.full_name.split()[0]}",
            "subtext": "Keep your streak alive.",
            "pal_score": pal_metrics["pal_score"],
            "time_spent_hours": round(total_time_seconds / 3600, 1),
            "total_time_seconds": total_time_seconds,
            "today_time_seconds": today_time_seconds,
            "last_session": last_session.to_dict() if last_session else None,
            "assignment_status": latest_assignment.status if latest_assignment else None,
            "streak_days": user.streak_days,
            "current_course": current_course,
            "rank": user_rank,
        },
        "stats": {
            "courses_completed": max(
                user.courses_completed,
                len([p for p in progress if p.status == 'completed'])
            ),
            "quizzes_submitted": quizzes_submitted,
            "cohort_rank": user.cohort_rank,
            "avg_quiz_score": quiz_avg,
        },
        "courses": course_rows,
        "tasks": task_rows,
        "leaderboard": leaderboard_data,
        "pal_breakdown": {
            "completion": completion_pct,
            "pal_quiz_avg": quiz_avg,
            "assignment_average": pal_metrics["assignment_average"],
            "task_completion": task_completion,
            "overall_pal_score": pal_metrics["pal_score"],
            "weights": pal_metrics["weights"],
            "current_rank": user_rank,
            "progress_trend": pal_metrics["progress_trend"],
            "strengths": pal_metrics["strengths"],
            "improvements": pal_metrics["improvements"],
        },
    }
