"""
AnalyticsRepository — powers all dashboard and reporting views.
Replaces the legacy raw SQL reporting from legacy_sql_repo.py.
Aggregates data using SQLAlchemy and the learner_events ledger.
"""

from __future__ import annotations

import json
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.user import User
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.enrollment import EnrollmentRequest
from app.models.pending_verification import PendingVerification
from app.models.task import Task
from app.models.audit import AuditLog
from app.models.pal import PalQuizScore
from app.repositories.base_repo import BaseRepository


class AnalyticsRepository(BaseRepository[LearnerEvent]):
    model = LearnerEvent

    @staticmethod
    def _round(value: float | int | None, digits: int = 1) -> float:
        return round(float(value or 0), digits)

    @staticmethod
    def _safe_json_list(raw: str | None) -> list[dict[str, Any]]:
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return []
        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def _iso(value: Any) -> str | None:
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _event_status(event_type: str) -> str:
        if event_type in {"COURSE_COMPLETED", "MODULE_COMPLETED", "QUIZ_SUBMITTED"}:
            return "success"
        if event_type in {"PROGRESS_MUTATION", "HEARTBEAT", "BLOCK_VIEWED"}:
            return "info"
        return "warning" if "FAILED" in event_type else "info"

    @staticmethod
    def _event_type(event_type: str) -> str:
        if "ENROLL" in event_type:
            return "enrollment"
        if "QUIZ" in event_type:
            return "pal"
        if "COURSE" in event_type or "MODULE" in event_type or "BLOCK" in event_type:
            return "course"
        return "system"

    @staticmethod
    def _event_title(event: LearnerEvent, learner_name: str, course_name: str | None, module_title: str | None) -> str:
        course_label = course_name or "course"
        module_label = module_title or "module"
        labels = {
            "COURSE_STARTED": f"{learner_name} started {course_label}",
            "COURSE_COMPLETED": f"{learner_name} completed {course_label}",
            "MODULE_COMPLETED": f"{learner_name} completed {module_label}",
            "BLOCK_VIEWED": f"{learner_name} viewed content in {course_label}",
            "HEARTBEAT": f"{learner_name} continued learning in {course_label}",
            "PROGRESS_MUTATION": f"{learner_name} progress updated in {course_label}",
            "QUIZ_SUBMITTED": f"{learner_name} submitted a quiz in {course_label}",
        }
        return labels.get(event.event_type, f"{learner_name} triggered {event.event_type.lower().replace('_', ' ')}")

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
        category_stmt = select(Category).where(Category.slug == category_slug, Category.status != "archived")
        if org_id:
            category_stmt = category_stmt.where(Category.org_id == org_id)
        category = self.session.execute(category_stmt).scalar_one_or_none()
        if not category:
            raise ValueError("Category not found.")

        course_stmt = select(Course).where(Course.status != "archived", Course.category_slug == category_slug)
        learner_stmt = select(User).where(User.role == "learner", User.category_scope == category_slug)
        enroll_stmt = select(EnrollmentRequest).where(
            EnrollmentRequest.category_slug == category_slug, 
            EnrollmentRequest.status.in_(["pending", "flagged"])
        )
        verification_stmt = select(func.count(PendingVerification.id)).where(PendingVerification.status == "pending")
        
        if org_id:
            course_stmt = course_stmt.where(Course.org_id == org_id)
            learner_stmt = learner_stmt.where(User.org_id == org_id)
            enroll_stmt = enroll_stmt.where(EnrollmentRequest.org_id == org_id)
            verification_stmt = verification_stmt.where(PendingVerification.organization_id == org_id)
            
        courses = self.session.execute(course_stmt).scalars().all()
        learners = self.session.execute(learner_stmt).scalars().all()
        pending_requests = self.session.execute(enroll_stmt).scalars().all()
        pending_verifications = self.session.execute(verification_stmt).scalar() or 0
        course_ids = [course.id for course in courses]
        learner_ids = [learner.id for learner in learners]

        module_rows = []
        progress_rows = []
        module_progress_rows = []
        latest_events = []
        if course_ids:
            module_stmt = (
                select(CourseModule)
                .where(CourseModule.course_id.in_(course_ids), CourseModule.deleted_at.is_(None))
                .order_by(CourseModule.course_id, CourseModule.section, CourseModule.sort_order, CourseModule.id)
            )
            progress_stmt = select(CourseProgress).where(CourseProgress.course_id.in_(course_ids))
            module_progress_stmt = (
                select(ModuleProgress)
                .join(CourseModule, CourseModule.id == ModuleProgress.module_id)
                .where(CourseModule.course_id.in_(course_ids), CourseModule.deleted_at.is_(None))
            )
            event_stmt = (
                select(LearnerEvent)
                .where(LearnerEvent.course_id.in_(course_ids))
                .order_by(desc(LearnerEvent.created_at))
                .limit(20)
            )
            if org_id:
                module_stmt = module_stmt.where(CourseModule.org_id == org_id)
                progress_stmt = progress_stmt.where(CourseProgress.org_id == org_id)
                module_progress_stmt = module_progress_stmt.where(ModuleProgress.org_id == org_id)
                event_stmt = event_stmt.where(LearnerEvent.org_id == org_id)
            module_rows = self.session.execute(module_stmt).scalars().all()
            progress_rows = self.session.execute(progress_stmt).scalars().all()
            module_progress_rows = self.session.execute(module_progress_stmt).scalars().all()
            latest_events = self.session.execute(event_stmt).scalars().all()

        modules_by_course: dict[str, list[CourseModule]] = {}
        module_title_by_id: dict[int, str] = {}
        for module in module_rows:
            modules_by_course.setdefault(module.course_id, []).append(module)
            module_title_by_id[module.id] = module.title

        normalized_by_user_course = {(row.user_id, row.course_id): row for row in progress_rows}
        legacy_by_user_course: dict[tuple[str, str], dict[str, Any]] = {}
        for learner in learners:
            for item in self._safe_json_list(learner.course_progress_json):
                course_id = item.get("course_id")
                if course_id:
                    legacy_by_user_course[(learner.id, course_id)] = item

        all_progress_keys = set(normalized_by_user_course) | set(legacy_by_user_course)
        progress_keys_by_course: dict[str, set[tuple[str, str]]] = {course.id: set() for course in courses}
        for key in all_progress_keys:
            if key[1] in progress_keys_by_course:
                progress_keys_by_course[key[1]].add(key)

        course_by_id = {course.id: course for course in courses}
        learner_by_id = {learner.id: learner for learner in learners}

        def progress_item(user_id: str, course_id: str) -> dict[str, Any]:
            row = normalized_by_user_course.get((user_id, course_id))
            if row:
                return {
                    "course_id": row.course_id,
                    "status": row.status,
                    "progress": self._round(row.completion_percentage, 0),
                    "completion_percentage": self._round(row.completion_percentage, 0),
                    "time_spent_seconds": row.time_spent_seconds,
                    "current_lesson": row.status.replace("_", " "),
                    "last_active": row.last_viewed_at.isoformat() if row.last_viewed_at else None,
                }
            legacy = legacy_by_user_course.get((user_id, course_id), {})
            return {
                "course_id": course_id,
                "status": legacy.get("status", "not_started"),
                "progress": self._round(legacy.get("progress", 0), 0),
                "completion_percentage": self._round(legacy.get("progress", 0), 0),
                "time_spent_seconds": 0,
                "current_lesson": legacy.get("current_lesson"),
                "last_active": None,
            }

        course_rows = []
        for course in courses:
            keys = progress_keys_by_course.get(course.id, set())
            enrolled_user_ids = {user_id for user_id, _ in keys}
            completed_count = 0
            for user_id, _ in keys:
                item = progress_item(user_id, course.id)
                if item["status"] == "completed" or item["completion_percentage"] >= 100:
                    completed_count += 1
            enrolled_count = len(enrolled_user_ids) or course.enrolled_count
            completion_rate = (completed_count / enrolled_count * 100.0) if enrolled_count else 0.0
            enrolled_pal = [learner_by_id[user_id].pal_score for user_id in enrolled_user_ids if user_id in learner_by_id]
            module_titles = [module.title for module in modules_by_course.get(course.id, [])]
            course_rows.append({
                "id": course.id,
                "moodle_course_id": course.moodle_course_id,
                "category_slug": course.category_slug,
                "name": course.name,
                "slug": course.slug,
                "description": course.description,
                "tier": course.tier,
                "status": course.status,
                "lessons_count": course.lessons_count,
                "hours": course.hours,
                "price_paise": course.price_paise,
                "org_id": course.org_id,
                "created_at": self._iso(course.created_at),
                "module_count": len(module_titles) or course.module_count,
                "modules": module_titles,
                "enrolled_count": enrolled_count,
                "completion_count": completed_count,
                "completion_rate": self._round(completion_rate),
                "completion_pct": self._round(completion_rate),
                "avg_pal_score": self._round(sum(enrolled_pal) / len(enrolled_pal), 1) if enrolled_pal else self._round(course.avg_quiz_score),
            })

        learner_rows = []
        completion_values = []
        time_values = []
        for learner in learners:
            keys = [key for key in all_progress_keys if key[0] == learner.id and key[1] in course_by_id]
            items = [progress_item(learner.id, course_id) for _, course_id in sorted(keys, key=lambda value: value[1])]
            completed = len([item for item in items if item["status"] == "completed" or item["completion_percentage"] >= 100])
            total_courses = len(items) or learner.total_courses or len(courses)
            avg_completion = sum(item["completion_percentage"] for item in items) / len(items) if items else learner.pal_completion_pct
            total_time_seconds = sum(item["time_spent_seconds"] for item in items)
            completion_values.append(avg_completion)
            time_values.append(total_time_seconds / 3600)
            learner_rows.append({
                "id": learner.id,
                "username": learner.username,
                "email": learner.email,
                "full_name": learner.full_name,
                "role": learner.role,
                "category_scope": learner.category_scope,
                "avatar_initials": learner.avatar_initials,
                "is_active": learner.is_active,
                "status": learner.status,
                "org_id": learner.org_id,
                "created_at": self._iso(learner.created_at),
                "enrollment_type": learner.enrollment_type or "manual",
                "avatar_gradient": [learner.gradient_start, learner.gradient_end],
                "current_course_id": learner.current_course_id,
                "total_courses": total_courses,
                "courses_completed": completed,
                "course_progress": items,
                "pal_score": self._round(learner.pal_score),
                "pal_completion_pct": self._round(avg_completion),
                "pal_quiz_avg": self._round(learner.pal_quiz_avg),
                "pal_time_spent_hours": self._round(total_time_seconds / 3600 if total_time_seconds else learner.pal_time_spent_hours),
                "pal_task_completion_pct": self._round(learner.pal_task_completion_pct),
                "last_active": max((item["last_active"] for item in items if item["last_active"]), default=None),
            })

        active_module_count = len([row for row in module_progress_rows if row.status in {"in_progress", "completed"}])
        avg_pal_score = sum(row["pal_score"] for row in learner_rows) / len(learner_rows) if learner_rows else 0.0
        avg_completion = sum(completion_values) / len(completion_values) if completion_values else 0.0
        avg_time_hours = sum(time_values) / len(time_values) if time_values else 0.0

        tasks = self.session.execute(select(Task).where(Task.category_slug == category_slug)).scalars().all()
        if org_id:
            tasks = [task for task in tasks if task.org_id == org_id]

        activity = []
        for event in latest_events:
            learner_name = learner_by_id.get(event.user_id).full_name if event.user_id in learner_by_id else "A learner"
            course_name = course_by_id.get(event.course_id).name if event.course_id in course_by_id else None
            activity.append({
                "id": f"learner-event-{event.id}",
                "type": self._event_type(event.event_type),
                "status": self._event_status(event.event_type),
                "title": self._event_title(event, learner_name, course_name, module_title_by_id.get(event.module_id)),
                "message": self._event_title(event, learner_name, course_name, module_title_by_id.get(event.module_id)),
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "event_type": event.event_type,
            })

        pal_leaderboard = sorted(learner_rows, key=lambda row: row["pal_score"], reverse=True)

        category_payload = {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "status": category.status,
            "accent_color": category.accent_color,
            "admin_user_id": category.admin_user_id,
            "planned_courses": category.planned_courses,
            "avg_pal_target": category.avg_pal_target,
            "org_id": category.org_id,
            "organization_id": category.organization_id,
            "org_type": category.org_type,
            "created_at": self._iso(category.created_at),
        }

        return {
            "category": category_payload,
            "kpis": {
                "total_courses": len(course_rows),
                "active_learners": len(learner_rows),
                "pending_enrollment": len(pending_requests),
                "pending_verifications": pending_verifications,
                "modules_started": active_module_count,
                "avg_pal_score": self._round(avg_pal_score),
                "avg_completion": self._round(avg_completion),
            },
            "courses": course_rows,
            "pending_enrollment": [
                {
                    "id": request.id,
                    "full_name": request.full_name,
                    "email": request.email,
                    "request_type": request.request_type,
                    "requested_at": request.requested_at,
                    "company_domain": request.company_domain,
                    "domain_verified": request.domain_verified,
                    "status": request.status,
                }
                for request in pending_requests
            ],
            "enrollment_requests": [
                {
                    "id": request.id,
                    "full_name": request.full_name,
                    "email": request.email,
                    "request_type": request.request_type,
                    "requested_at": request.requested_at,
                    "company_domain": request.company_domain,
                    "domain_verified": request.domain_verified,
                    "status": request.status,
                }
                for request in pending_requests
            ],
            "learners": {"total": len(learner_rows), "rows": learner_rows},
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "assigned_label": task.assigned_label,
                    "assigned_to_user_id": task.assigned_to_user_id,
                    "assignment_scope": task.assignment_scope,
                    "category_slug": task.category_slug,
                    "due_at": task.due_at,
                    "status": task.status,
                    "assigned_by": task.assigned_by,
                    "notes": task.notes,
                    "is_cross_category": task.is_cross_category,
                    "org_id": task.org_id,
                    "created_at": self._iso(task.created_at),
                }
                for task in tasks
            ],
            "activity": activity,
            "pal": {
                "summary": {
                    "avg_completion": self._round(avg_completion),
                    "avg_quiz_score": self._round(sum(row["pal_quiz_avg"] for row in learner_rows) / len(learner_rows), 1) if learner_rows else 0.0,
                    "avg_time_hours": self._round(avg_time_hours),
                },
                "leaderboard": pal_leaderboard,
                "chart": [{"name": row["full_name"].split()[0], "score": row["pal_score"]} for row in pal_leaderboard],
            },
            "leaderboard": pal_leaderboard[:4],
        }

    def get_stats_breakdown(self, category_slug: str, org_id: int | None = None) -> dict[str, Any]:
        """Provides metrics for deep-dive Stats Dashboard."""
        metrics = self.get_category_metrics(category_slug, org_id)
        return {
            "category": metrics["category"],
            "kpis": {
                "active_courses": metrics["kpis"]["total_courses"],
                "enrolled_learners": metrics["kpis"]["active_learners"],
                "avg_completion": metrics["kpis"]["avg_completion"],
            },
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
