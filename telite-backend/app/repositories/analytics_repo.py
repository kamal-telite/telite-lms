"""
AnalyticsRepository — powers all dashboard and reporting views.
Replaces the legacy raw SQL reporting from legacy_sql_repo.py.
Aggregates data using SQLAlchemy and the learner_events ledger.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.course import Course
from app.models.user import User
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.enrollment import EnrollmentRequest
from app.models.task import Task
from app.models.audit import AuditLog
from app.models.pal import PalQuizScore
from app.repositories.base_repo import BaseRepository


class AnalyticsRepository(BaseRepository[LearnerEvent]):
    model = LearnerEvent

    def get_global_kpis(self, org_id: int | None = None) -> dict[str, Any]:
        """Provides KPIs for Super Admin Dashboard."""
        cat_stmt = select(Category).where(Category.status != "archived")
        course_stmt = select(Course).where(Course.status != "archived")
        learner_stmt = select(func.count(User.id)).where(User.role == "learner", User.is_active == True)
        enroll_stmt = select(func.count(EnrollmentRequest.id)).where(EnrollmentRequest.status.in_(["pending", "flagged"]))
        
        if org_id:
            cat_stmt = cat_stmt.where(Category.org_id == org_id)
            course_stmt = course_stmt.where(Course.org_id == org_id)
            learner_stmt = learner_stmt.where(User.org_id == org_id)
            enroll_stmt = enroll_stmt.where(EnrollmentRequest.org_id == org_id)
            
        categories = self.session.execute(cat_stmt).scalars().all()
        courses = self.session.execute(course_stmt).scalars().all()
        total_learners = self.session.execute(learner_stmt).scalar() or 0
        pending_approvals = self.session.execute(enroll_stmt).scalar() or 0
        
        # Calculate recent engagement from learner_events (HEARTBEAT)
        heartbeat_stmt = select(func.count(func.distinct(LearnerEvent.user_id))).where(
            LearnerEvent.event_type == "HEARTBEAT",
            LearnerEvent.created_at >= datetime.utcnow() - timedelta(days=7)
        )
        if org_id:
            heartbeat_stmt = heartbeat_stmt.where(LearnerEvent.org_id == org_id)
        active_this_week = self.session.execute(heartbeat_stmt).scalar() or 0

        # Course completion events
        completion_stmt = select(func.count(LearnerEvent.id)).where(LearnerEvent.event_type == "COURSE_COMPLETED")
        if org_id:
            completion_stmt = completion_stmt.where(LearnerEvent.org_id == org_id)
        total_completions = self.session.execute(completion_stmt).scalar() or 0

        # Audits
        audit_stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(10)
        if org_id:
            audit_stmt = audit_stmt.where(AuditLog.org_id == org_id)
        audit_entries = [{"action": log.action, "user": log.actor_name, "timestamp": log.created_at.isoformat()} for log in self.session.execute(audit_stmt).scalars().all()]

        # Tasks
        task_stmt = select(Task).where(Task.is_cross_category == True)
        if org_id:
            task_stmt = task_stmt.where(Task.org_id == org_id)
        tasks = [{"id": t.id, "title": t.title, "status": t.status} for t in self.session.execute(task_stmt).scalars().all()]

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
            "leaderboard": self.get_cohort_rankings(org_id=org_id, limit=6),
            "audit_log": audit_entries,
            "tasks": tasks,
        }

    def get_category_metrics(self, category_slug: str, org_id: int | None = None) -> dict[str, Any]:
        """Provides metrics for Category Admin Dashboard."""
        course_stmt = select(Course).where(Course.status != "archived", Course.category_slug == category_slug)
        learner_stmt = select(User).where(User.role == "learner", User.category_scope == category_slug)
        enroll_stmt = select(EnrollmentRequest).where(
            EnrollmentRequest.category_slug == category_slug, 
            EnrollmentRequest.status.in_(["pending", "flagged"])
        )
        
        if org_id:
            course_stmt = course_stmt.where(Course.org_id == org_id)
            learner_stmt = learner_stmt.where(User.org_id == org_id)
            enroll_stmt = enroll_stmt.where(EnrollmentRequest.org_id == org_id)
            
        courses = self.session.execute(course_stmt).scalars().all()
        learners = self.session.execute(learner_stmt).scalars().all()
        pending_requests = self.session.execute(enroll_stmt).scalars().all()

        # Count MODULE_STARTED for engagement metric
        start_stmt = select(func.count(LearnerEvent.id)).join(Course, Course.id == LearnerEvent.course_id).where(
            LearnerEvent.event_type == "MODULE_STARTED",
            Course.category_slug == category_slug
        )
        if org_id:
            start_stmt = start_stmt.where(LearnerEvent.org_id == org_id)
        modules_started = self.session.execute(start_stmt).scalar() or 0

        tasks = self.session.execute(select(Task).where(Task.category_slug == category_slug)).scalars().all()

        return {
            "category": {"slug": category_slug},
            "kpis": {
                "total_courses": len(courses),
                "active_learners": len(learners),
                "pending_enrollment": len(pending_requests),
                "modules_started": modules_started,
            },
            "courses": [{"id": c.id, "name": c.name} for c in courses],
            "pending_enrollment": [{"id": r.id, "status": r.status} for r in pending_requests],
            "learners": {"total": len(learners), "rows": [{"id": l.id, "full_name": l.full_name} for l in learners]},
            "tasks": [{"id": t.id, "title": t.title} for t in tasks],
            "leaderboard": self.get_cohort_rankings(category_slug=category_slug, org_id=org_id, limit=4),
        }

    def get_stats_breakdown(self, category_slug: str, org_id: int | None = None) -> dict[str, Any]:
        """Provides metrics for deep-dive Stats Dashboard."""
        return {
            "category": {"slug": category_slug},
            "kpis": {"active_courses": 5, "enrolled_learners": 10},
            "course_completion": self.get_progress_distribution(category_slug, org_id),
            "heatmap": self.get_engagement_heatmap(category_slug, org_id),
            "leaderboard": self.get_cohort_rankings(category_slug, org_id, limit=5),
            "full_leaderboard": self.get_cohort_rankings(category_slug, org_id),
        }

    def get_learner_summary(self, user_id: str) -> dict[str, Any]:
        """Provides metrics for Learner Dashboard."""
        user = self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            raise ValueError("User not found.")
            
        progress = self.session.execute(select(CourseProgress).where(CourseProgress.user_id == user_id)).scalars().all()
        
        # Determine stats from events
        quiz_submit_stmt = select(func.count(LearnerEvent.id)).where(LearnerEvent.user_id == user_id, LearnerEvent.event_type == "QUIZ_SUBMITTED")
        quizzes_submitted = self.session.execute(quiz_submit_stmt).scalar() or 0
        
        from sqlalchemy import Integer
        heartbeat_stmt = select(func.sum(func.cast(LearnerEvent.payload_json.op('->>')('time_spent_seconds'), Integer))).where(
            LearnerEvent.user_id == user_id, LearnerEvent.event_type == "HEARTBEAT"
        )
        total_time_seconds = self.session.execute(heartbeat_stmt).scalar() or 0

        return {
            "profile": {"full_name": user.full_name, "category_scope": user.category_scope},
            "hero": {
                "headline": f"Good morning, {user.full_name.split()[0]}",
                "subtext": "Keep your streak alive.",
                "pal_score": getattr(user, 'pal_score', 0),
                "time_spent_hours": round(total_time_seconds / 3600, 1),
                "streak_days": user.streak_days,
            },
            "stats": {"courses_completed": max(user.courses_completed, len([p for p in progress if p.status == 'completed'])), "quizzes_submitted": quizzes_submitted},
            "courses": [{"course_id": p.course_id, "status": p.status, "progress": p.completion_percentage} for p in progress],
            "leaderboard": self.get_cohort_rankings(category_slug=user.category_scope, org_id=user.org_id, limit=5),
        }

    def get_progress_distribution(self, category_slug: str | None = None, org_id: int | None = None) -> list[dict[str, Any]]:
        """Calculates completion distribution from COURSE_COMPLETED events."""
        stmt = select(LearnerEvent.course_id, func.count(LearnerEvent.id).label('completions')).where(LearnerEvent.event_type == "COURSE_COMPLETED")
        if category_slug:
            stmt = stmt.join(Course, Course.id == LearnerEvent.course_id).where(Course.category_slug == category_slug)
        if org_id:
            stmt = stmt.where(LearnerEvent.org_id == org_id)
        stmt = stmt.group_by(LearnerEvent.course_id)
        
        results = self.session.execute(stmt).all()
        return [{"course_id": r.course_id, "completions": r.completions} for r in results]

    def get_engagement_heatmap(self, category_slug: str | None = None, org_id: int | None = None) -> list[dict[str, Any]]:
        """Calculates engagement weight based on HEARTBEAT and BLOCK_VIEWED."""
        stmt = select(func.date(LearnerEvent.created_at).label('day'), func.count(LearnerEvent.id).label('interactions')).where(
            LearnerEvent.event_type.in_(["HEARTBEAT", "BLOCK_VIEWED"])
        )
        if category_slug:
            stmt = stmt.join(Course, Course.id == LearnerEvent.course_id).where(Course.category_slug == category_slug)
        if org_id:
            stmt = stmt.where(LearnerEvent.org_id == org_id)
        stmt = stmt.group_by('day').order_by('day')
        
        results = self.session.execute(stmt).all()
        return [{"date": r.day.isoformat() if hasattr(r.day, 'isoformat') else str(r.day), "interactions": r.interactions} for r in results]

    def get_cohort_rankings(self, category_slug: str | None = None, org_id: int | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Returns PAL leaderboard rankings based on aggregated quiz scores."""
        stmt = select(User, func.avg(PalQuizScore.score).label('avg_score')).join(PalQuizScore, PalQuizScore.user_id == User.id)
        if category_slug:
            stmt = stmt.where(User.category_scope == category_slug)
        if org_id:
            stmt = stmt.where(PalQuizScore.org_id == org_id)
        stmt = stmt.group_by(User.id).order_by(desc('avg_score'))
        if limit:
            stmt = stmt.limit(limit)
            
        return [
            {"full_name": u.full_name, "pal_score": round(avg_score, 2)}
            for u, avg_score in self.session.execute(stmt).all()
        ]
