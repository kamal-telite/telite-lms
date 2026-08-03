"""Global/super-admin analytics queries."""

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.course import Course
from app.models.user import User
from app.models.learner_event import LearnerEvent
from app.models.enrollment import EnrollmentRequest
from app.models.audit import AuditLog
from app.models.task import Task
from app.repositories.analytics.utils import iso_format


def get_global_kpis(session: Session, org_id: int | None = None) -> dict[str, Any]:
    """Provides KPIs for Super Admin Dashboard."""
    cat_stmt = select(Category).where(Category.status != "archived")
    course_stmt = select(Course).where(Course.status != "archived")
    learner_stmt = select(func.count(User.id)).where(
        User.role == "learner",
        User.is_active == True
    )
    enroll_stmt = select(func.count(EnrollmentRequest.id)).where(
        EnrollmentRequest.status.in_(["pending", "flagged"])
    )
    
    if org_id:
        cat_stmt = cat_stmt.where(Category.org_id == org_id)
        course_stmt = course_stmt.where(Course.org_id == org_id)
        learner_stmt = learner_stmt.where(User.org_id == org_id)
        enroll_stmt = enroll_stmt.where(EnrollmentRequest.org_id == org_id)
        
    categories = session.execute(cat_stmt).scalars().all()
    courses = session.execute(course_stmt).scalars().all()
    total_learners = session.execute(learner_stmt).scalar() or 0
    pending_approvals = session.execute(enroll_stmt).scalar() or 0
    
    # Calculate recent engagement from learner_events (HEARTBEAT)
    heartbeat_stmt = select(func.count(func.distinct(LearnerEvent.user_id))).where(
        LearnerEvent.event_type == "HEARTBEAT",
        LearnerEvent.created_at >= datetime.utcnow() - timedelta(days=7)
    )
    if org_id:
        heartbeat_stmt = heartbeat_stmt.where(LearnerEvent.org_id == org_id)
    active_this_week = session.execute(heartbeat_stmt).scalar() or 0

    # Course completion events
    completion_stmt = select(func.count(LearnerEvent.id)).where(
        LearnerEvent.event_type == "COURSE_COMPLETED"
    )
    if org_id:
        completion_stmt = completion_stmt.where(LearnerEvent.org_id == org_id)
    total_completions = session.execute(completion_stmt).scalar() or 0

    # Audits
    audit_stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(10)
    if org_id:
        audit_stmt = audit_stmt.where(AuditLog.org_id == org_id)
    audit_entries = [
        {
            "action": log.action,
            "user": log.actor_name,
            "timestamp": log.created_at.isoformat()
        }
        for log in session.execute(audit_stmt).scalars().all()
    ]

    # Tasks
    task_stmt = select(Task).where(Task.is_cross_category == True)
    if org_id:
        task_stmt = task_stmt.where(Task.org_id == org_id)
    tasks = [
        {"id": t.id, "title": t.title, "status": t.status}
        for t in session.execute(task_stmt).scalars().all()
    ]

    return {
        "kpis": {
            "total_categories": len(categories),
            "total_courses": len(courses),
            "total_learners": total_learners,
            "pending_approvals": pending_approvals,
            "active_this_week": active_this_week,
            "total_completions": total_completions,
        },
        "categories": [{"name": c.name, "slug": c.slug} for c in categories],
        "learners": {"total": total_learners, "rows": []},
        "leaderboard": get_cohort_rankings(session, org_id=org_id, limit=6),
        "audit_log": audit_entries,
        "tasks": tasks,
    }


def get_cohort_rankings(
    session: Session,
    category_slug: str | None = None,
    org_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get PAL score rankings for the cohort."""
    from app.models.user import User
    
    stmt = select(User).where(
        User.role == "learner",
        User.is_active == True,
    )

    if category_slug:
        stmt = stmt.where(User.category_scope == category_slug)
    if org_id:
        stmt = stmt.where(User.org_id == org_id)

    stmt = stmt.order_by(User.pal_score.desc()).limit(limit)
    learners = session.execute(stmt).scalars().all()
    
    return [
        {
            "id": learner.id,
            "full_name": learner.full_name,
            "pal_score": learner.pal_score or 0,
            "avatar_initials": learner.avatar_initials,
            "avatar_gradient": [learner.gradient_start, learner.gradient_end],
        }
        for learner in learners
    ]
