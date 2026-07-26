"""Engagement and progress distribution analytics."""

from typing import Any
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.learner_event import LearnerEvent
from app.models.course import Course
from app.repositories.analytics.utils import round_value


def get_progress_distribution(
    session: Session,
    category_slug: str | None = None,
    org_id: int | None = None
) -> list[dict[str, Any]]:
    """Calculates completion distribution from COURSE_COMPLETED events."""
    stmt = select(
        LearnerEvent.course_id,
        func.count(LearnerEvent.id).label('completions')
    ).where(LearnerEvent.event_type == "COURSE_COMPLETED")
    
    if category_slug:
        stmt = stmt.join(
            Course, Course.id == LearnerEvent.course_id
        ).where(Course.category_slug == category_slug)
    if org_id:
        stmt = stmt.where(LearnerEvent.org_id == org_id)
    
    stmt = stmt.group_by(LearnerEvent.course_id)
    
    results = session.execute(stmt).all()
    return [
        {"course_id": r.course_id, "completions": r.completions}
        for r in results
    ]


def get_engagement_heatmap(
    session: Session,
    category_slug: str | None = None,
    org_id: int | None = None
) -> list[dict[str, Any]]:
    """Calculates engagement weight based on HEARTBEAT, BLOCK_VIEWED, and interactive blocks."""
    stmt = select(
        func.date(LearnerEvent.created_at).label('day'),
        func.count(LearnerEvent.id).label('interactions')
    ).where(
        LearnerEvent.event_type.in_(["HEARTBEAT", "BLOCK_VIEWED", "POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED", "QUIZ_SUBMITTED"])
    )
    
    if category_slug:
        stmt = stmt.join(
            Course, Course.id == LearnerEvent.course_id
        ).where(Course.category_slug == category_slug)
    if org_id:
        stmt = stmt.where(LearnerEvent.org_id == org_id)
    
    stmt = stmt.group_by('day').order_by('day')
    
    results = session.execute(stmt).all()
    return [
        {
            "date": r.day.isoformat() if hasattr(r.day, 'isoformat') else str(r.day),
            "interactions": r.interactions
        }
        for r in results
    ]
