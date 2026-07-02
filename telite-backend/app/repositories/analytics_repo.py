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
from app.models.organization import Organization
from app.models.session import AuthSession
from app.models.user import User
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.enrollment import EnrollmentRequest
from app.models.pending_verification import PendingVerification
from app.models.task import Task
from app.models.task_workflow import TaskAssignment
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
        if event_type in {"COURSE_COMPLETED", "MODULE_COMPLETED", "BLOCK_COMPLETED", "QUIZ_SUBMITTED"}:
            return "success"
        if event_type in {"PROGRESS_MUTATION", "HEARTBEAT", "BLOCK_VIEWED", "POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED"}:
            return "info"
        return "warning" if "FAILED" in event_type else "info"

    @staticmethod
    def _event_type(event_type: str) -> str:
        if "ENROLL" in event_type:
            return "enrollment"
        if "QUIZ" in event_type:
            return "pal"
        if "COURSE" in event_type or "MODULE" in event_type or "BLOCK" in event_type or event_type in ["POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED"]:
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
            "BLOCK_COMPLETED": f"{learner_name} completed an interactive block",
            "BLOCK_VIEWED": f"{learner_name} viewed content in {course_label}",
            "HEARTBEAT": f"{learner_name} continued learning in {course_label}",
            "PROGRESS_MUTATION": f"{learner_name} progress updated in {course_label}",
            "QUIZ_SUBMITTED": f"{learner_name} submitted a quiz in {course_label}",
            "POLL_VOTED": f"{learner_name} voted in a poll",
            "FLASHCARD_FLIPPED": f"{learner_name} flipped a flashcard",
            "RESOURCE_DOWNLOADED": f"{learner_name} downloaded a resource",
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
            "learners": {"total": total_learners, "rows": []},
            "leaderboard": self.get_cohort_rankings(org_id=org_id, limit=6),
            "audit_log": audit_entries,
            "tasks": tasks,
        }

    def get_platform_overview(self) -> dict[str, Any]:
        """Return the strict platform overview contract consumed by admin UI."""
        total_orgs = self.session.execute(select(func.count(Organization.id))).scalar() or 0
        total_users = self.session.execute(select(func.count(User.id))).scalar() or 0
        active_sessions = (
            self.session.execute(
                select(func.count(AuthSession.id)).where(AuthSession.revoked_at.is_(None))
            ).scalar()
            or 0
        )
        recent_events = (
            self.session.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(10))
            .scalars()
            .all()
        )

        return {
            "total_orgs": total_orgs,
            "total_users": total_users,
            "active_sessions": active_sessions,
            "recent_activity": [
                {
                    "id": event.id,
                    "action": event.action,
                    "actor_name": event.actor_name,
                    "message": event.message,
                    "created_at": self._iso(event.created_at),
                    "org_id": event.org_id,
                }
                for event in recent_events
            ],
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
        progress_by_course = {row.course_id: row for row in progress}
        legacy_progress = {
            item.get("course_id"): item
            for item in self._safe_json_list(user.course_progress_json)
            if item.get("course_id")
        }

        course_stmt = select(Course).where(
            Course.org_id == user.org_id,
            Course.status.in_(("active", "published")),
        )
        if user.role == "learner" and user.category_scope:
            course_stmt = course_stmt.where(Course.category_slug == user.category_scope)
        courses = list(self.session.execute(course_stmt.order_by(Course.name)).scalars().all())

        approved_enrollments = self.session.execute(
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
                completion_pct = self._round(row.completion_percentage, 0)
                time_spent_seconds = row.time_spent_seconds
                last_active = row.last_viewed_at.isoformat() if row.last_viewed_at else None
            else:
                learner_status = legacy.get("status", "not_started")
                completion_pct = self._round(legacy.get("progress", 0), 0)
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
            }

        course_rows = [course_progress_payload(course) for course in courses]
        course_by_id = {course.id: course for course in courses}
        current_course = None
        if user.current_course_id and user.current_course_id in course_by_id:
            current_course = course_progress_payload(course_by_id[user.current_course_id])
        elif progress:
            latest_progress = max(progress, key=lambda row: row.last_viewed_at or row.updated_at or row.created_at)
            if latest_progress.course_id in course_by_id:
                current_course = course_progress_payload(course_by_id[latest_progress.course_id])
        elif course_rows:
            current_course = course_rows[0]
        
        # Determine stats from events
        quiz_submit_stmt = select(func.count(LearnerEvent.id)).where(LearnerEvent.user_id == user_id, LearnerEvent.event_type == "QUIZ_SUBMITTED")
        quizzes_submitted = self.session.execute(quiz_submit_stmt).scalar() or 0
        
        from sqlalchemy import Integer
        heartbeat_stmt = select(func.sum(func.cast(LearnerEvent.payload_json.op('->>')('time_spent_seconds'), Integer))).where(
            LearnerEvent.user_id == user_id, LearnerEvent.event_type == "HEARTBEAT"
        )
        total_time_seconds = self.session.execute(heartbeat_stmt).scalar() or 0

        # Calculate PAL breakdown from user fields and progress
        completed_courses_count = len([p for p in progress if p.status == 'completed'])
        total_courses_count = len(courses) or 1
        completion_pct = (completed_courses_count / total_courses_count * 100.0) if total_courses_count else 0.0
        
        # Get quiz average from PalQuizScore or user.pal_quiz_avg
        quiz_avg = user.pal_quiz_avg if hasattr(user, 'pal_quiz_avg') else 0.0
        
        # Task completion from user field
        task_completion = user.pal_task_completion_pct if hasattr(user, 'pal_task_completion_pct') else 0.0

        task_stmt = (
            select(Task, TaskAssignment, User)
            .join(TaskAssignment, TaskAssignment.task_id == Task.id)
            .outerjoin(User, User.id == Task.assigned_by)
            .where(TaskAssignment.learner_id == user_id)
            .where(Task.org_id == user.org_id)
            .order_by(TaskAssignment.updated_at.desc().nullslast(), TaskAssignment.assigned_at.desc())
        )
        task_rows = []
        for task, assignment, assigner in self.session.execute(task_stmt).all():
            task_rows.append(
                {
                    "id": task.id,
                    "assignment_id": assignment.id,
                    "title": task.title,
                    "description": task.description,
                    "instructions": task.notes or task.description or "",
                    "assigned_by": task.assigned_by,
                    "assigned_by_name": assigner.full_name if assigner else "Category Admin",
                    "assigned_label": task.assigned_label,
                    "assigned_to_user_id": task.assigned_to_user_id,
                    "category_slug": task.category_slug,
                    "due_at": task.due_at,
                    "status": assignment.status,
                    "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
                    "started_at": assignment.started_at.isoformat() if assignment.started_at else None,
                    "submitted_at": assignment.submitted_at.isoformat() if assignment.submitted_at else None,
                    "completed_at": assignment.completed_at.isoformat() if assignment.completed_at else None,
                }
            )

        # Get leaderboard and calculate user's rank
        leaderboard_data = self.get_cohort_rankings(category_slug=user.category_scope, org_id=user.org_id, limit=50)
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
                "pal_score": getattr(user, 'pal_score', 0),
                "time_spent_hours": round(total_time_seconds / 3600, 1),
                "streak_days": user.streak_days,
                "current_course": current_course,
                "rank": user_rank,
            },
            "stats": {
                "courses_completed": max(user.courses_completed, len([p for p in progress if p.status == 'completed'])),
                "quizzes_submitted": quizzes_submitted,
                "cohort_rank": user.cohort_rank,
                "avg_quiz_score": quiz_avg,
            },
            "courses": course_rows,
            "tasks": task_rows,
            "pal_breakdown": {
                "completion": completion_pct,
                "pal_quiz_avg": quiz_avg,
                "task_completion": task_completion,
            },
            "recommendation": {
                "leaderboard": leaderboard_data[:5],
            },
            "leaderboard": leaderboard_data[:5],
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
        """Calculates engagement weight based on HEARTBEAT, BLOCK_VIEWED, and interactive blocks."""
        stmt = select(func.date(LearnerEvent.created_at).label('day'), func.count(LearnerEvent.id).label('interactions')).where(
            LearnerEvent.event_type.in_(["HEARTBEAT", "BLOCK_VIEWED", "POLL_VOTED", "FLASHCARD_FLIPPED", "RESOURCE_DOWNLOADED", "QUIZ_SUBMITTED"])
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
        # Use LEFT JOIN to include users without quiz scores
        stmt = select(
            User.id,
            User.full_name,
            func.coalesce(func.avg(PalQuizScore.score), 0.0).label('avg_score'),
            User.streak_days,
            User.pal_score
        ).outerjoin(PalQuizScore, PalQuizScore.user_id == User.id)
        
        if category_slug:
            stmt = stmt.where(User.category_scope == category_slug)
        if org_id:
            stmt = stmt.where(User.org_id == org_id)
        
        stmt = stmt.group_by(User.id, User.full_name, User.streak_days, User.pal_score).order_by(desc('avg_score'))
        if limit:
            stmt = stmt.limit(limit)
            
        results = self.session.execute(stmt).all()
        return [
            {
                "id": row.id,
                "full_name": row.full_name,
                "pal_score": round(float(row.avg_score), 2),
                "streak_days": row.streak_days or 0,
                "rank": idx + 1,
            }
            for idx, row in enumerate(results)
        ]

    def get_grading_analytics_super_admin(self, org_id: int | None = None) -> dict[str, Any]:
        """Returns organization-wide grading analytics for Super Admin dashboard."""
        from app.models.gradebook import CourseGrade, GradeResult, GradeItem, GradeCategory
        
        # Base queries with org filter
        course_grade_stmt = select(CourseGrade)
        grade_result_stmt = select(GradeResult)
        grade_item_stmt = select(GradeItem)
        
        if org_id:
            course_grade_stmt = course_grade_stmt.where(CourseGrade.org_id == org_id)
            grade_result_stmt = grade_result_stmt.where(GradeResult.org_id == org_id)
            grade_item_stmt = grade_item_stmt.where(GradeItem.org_id == org_id)
        
        # Calculate overall statistics
        total_grades = self.session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
        
        if org_id:
            total_grades = self.session.execute(
                select(func.count(CourseGrade.id)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar() or 0
        
        # Average grade
        avg_grade_result = self.session.execute(
            select(func.avg(CourseGrade.percentage)).where(
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar()
        
        if org_id:
            avg_grade_result = self.session.execute(
                select(func.avg(CourseGrade.percentage)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar()
        
        overall_average = self._round(avg_grade_result) if avg_grade_result else 0.0
        
        # Pass rate (grades >= 60%)
        pass_count = self.session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.percentage >= 60.0,
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
        
        if org_id:
            pass_count = self.session.execute(
                select(func.count(CourseGrade.id)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.percentage >= 60.0,
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar() or 0
        
        pass_rate = self._round((pass_count / total_grades * 100.0) if total_grades > 0 else 0.0)
        fail_rate = self._round(100.0 - pass_rate) if total_grades > 0 else 0.0
        
        # Total assessments (grade items)
        total_assessments = self.session.execute(
            select(func.count(GradeItem.id)).where(GradeItem.deleted_at.is_(None))
        ).scalar() or 0
        
        if org_id:
            total_assessments = self.session.execute(
                select(func.count(GradeItem.id)).where(
                    GradeItem.org_id == org_id,
                    GradeItem.deleted_at.is_(None)
                )
            ).scalar() or 0
        
        # Total graded learners (unique users with course grades)
        total_graded_learners = self.session.execute(
            select(func.count(func.distinct(CourseGrade.user_id))).where(
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
        
        if org_id:
            total_graded_learners = self.session.execute(
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
            grade_distribution[i]["count"] = self.session.execute(count_stmt).scalar() or 0
        
        # Top performing categories (by average grade)
        category_performance = self.session.execute(
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
            .limit(5)
        ).all()
        
        if org_id:
            category_performance = self.session.execute(
                select(
                    GradeCategory.name,
                    func.avg(CourseGrade.percentage).label('avg_grade')
                )
                .join(GradeItem, GradeItem.category_id == GradeCategory.id)
                .join(GradeResult, GradeResult.grade_item_id == GradeItem.id)
                .join(CourseGrade, CourseGrade.user_id == GradeResult.user_id)
                .where(
                    GradeCategory.org_id == org_id,
                    GradeCategory.deleted_at.is_(None),
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
                .group_by(GradeCategory.id, GradeCategory.name)
                .order_by(desc('avg_grade'))
                .limit(5)
            ).all()
        
        top_categories = [
            {"name": name, "average": self._round(avg_grade)}
            for name, avg_grade in category_performance
        ]
        
        # Lowest performing categories
        lowest_categories = list(reversed(top_categories[-3:])) if len(top_categories) > 3 else []
        
        # Organization grade trend (last 6 months)
        from datetime import datetime, timedelta
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        trend_data = []
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            
            month_avg = self.session.execute(
                select(func.avg(CourseGrade.percentage)).where(
                    CourseGrade.calculated_at >= month_start,
                    CourseGrade.calculated_at < month_end,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar()
            
            if org_id:
                month_avg = self.session.execute(
                    select(func.avg(CourseGrade.percentage)).where(
                        CourseGrade.org_id == org_id,
                        CourseGrade.calculated_at >= month_start,
                        CourseGrade.calculated_at < month_end,
                        CourseGrade.percentage.isnot(None),
                        CourseGrade.status.in_(["calculated", "released"])
                    )
                ).scalar()
            
            trend_data.append({
                "month": month_start.strftime("%b"),
                "average": self._round(month_avg) if month_avg else 0.0
            })
        
        return {
            "overall_average": overall_average,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "grade_distribution": grade_distribution,
            "top_categories": top_categories,
            "lowest_categories": lowest_categories,
            "total_assessments": total_assessments,
            "total_graded_learners": total_graded_learners,
            "grade_trend": trend_data,
        }

    def get_grading_analytics_category_admin(self, category_slug: str, org_id: int | None = None) -> dict[str, Any]:
        """Returns category-specific grading analytics for Category Admin dashboard."""
        from app.models.gradebook import CourseGrade, GradeResult, GradeItem, GradeCategory
        
        # Get category courses
        category_stmt = select(Category).where(Category.slug == category_slug)
        if org_id:
            category_stmt = category_stmt.where(Category.org_id == org_id)
        category = self.session.execute(category_stmt).scalar_one_or_none()
        
        if not category:
            return {}
        
        course_stmt = select(Course).where(
            Course.category_slug == category_slug,
            Course.status != "archived"
        )
        if org_id:
            course_stmt = course_stmt.where(Course.org_id == org_id)
        courses = self.session.execute(course_stmt).scalars().all()
        course_ids = [c.id for c in courses]
        
        if not course_ids:
            return {
                "average_grade": 0.0,
                "pass_rate": 0.0,
                "fail_rate": 0.0,
                "quiz_average": 0.0,
                "assignment_average": 0.0,
                "course_grade_distribution": [],
                "learners_at_risk": [],
                "top_performers": [],
                "grade_trend": [],
                "grade_summary": {"total_graded": 0, "total_assessments": 0}
            }
        
        # Average grade for category
        avg_grade_result = self.session.execute(
            select(func.avg(CourseGrade.percentage)).where(
                CourseGrade.course_id.in_(course_ids),
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar()
        
        if org_id:
            avg_grade_result = self.session.execute(
                select(func.avg(CourseGrade.percentage)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar()
        
        average_grade = self._round(avg_grade_result) if avg_grade_result else 0.0
        
        # Pass/fail rates
        total_grades = self.session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.course_id.in_(course_ids),
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
        
        if org_id:
            total_grades = self.session.execute(
                select(func.count(CourseGrade.id)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar() or 0
        
        pass_count = self.session.execute(
            select(func.count(CourseGrade.id)).where(
                CourseGrade.course_id.in_(course_ids),
                CourseGrade.percentage >= 60.0,
                CourseGrade.status.in_(["calculated", "released"])
            )
        ).scalar() or 0
        
        if org_id:
            pass_count = self.session.execute(
                select(func.count(CourseGrade.id)).where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.percentage >= 60.0,
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar() or 0
        
        pass_rate = self._round((pass_count / total_grades * 100.0) if total_grades > 0 else 0.0)
        fail_rate = self._round(100.0 - pass_rate) if total_grades > 0 else 0.0
        
        # Quiz average (from grade results with source_type = quiz_block)
        quiz_avg_result = self.session.execute(
            select(func.avg(GradeResult.percentage)).where(
                GradeResult.course_id.in_(course_ids),
                GradeResult.source_type == "quiz_block",
                GradeResult.percentage.isnot(None),
                GradeResult.status == "graded"
            )
        ).scalar()
        
        if org_id:
            quiz_avg_result = self.session.execute(
                select(func.avg(GradeResult.percentage)).where(
                    GradeResult.org_id == org_id,
                    GradeResult.course_id.in_(course_ids),
                    GradeResult.source_type == "quiz_block",
                    GradeResult.percentage.isnot(None),
                    GradeResult.status == "graded"
                )
            ).scalar()
        
        quiz_average = self._round(quiz_avg_result) if quiz_avg_result else 0.0
        
        # Assignment average (from grade results with source_type = assignment_block)
        assignment_avg_result = self.session.execute(
            select(func.avg(GradeResult.percentage)).where(
                GradeResult.course_id.in_(course_ids),
                GradeResult.source_type == "assignment_block",
                GradeResult.percentage.isnot(None),
                GradeResult.status == "graded"
            )
        ).scalar()
        
        if org_id:
            assignment_avg_result = self.session.execute(
                select(func.avg(GradeResult.percentage)).where(
                    GradeResult.org_id == org_id,
                    GradeResult.course_id.in_(course_ids),
                    GradeResult.source_type == "assignment_block",
                    GradeResult.percentage.isnot(None),
                    GradeResult.status == "graded"
                )
            ).scalar()
        
        assignment_average = self._round(assignment_avg_result) if assignment_avg_result else 0.0
        
        # Course grade distribution
        course_distribution = []
        for course in courses:
            course_avg = self.session.execute(
                select(func.avg(CourseGrade.percentage)).where(
                    CourseGrade.course_id == course.id,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar()
            
            if org_id:
                course_avg = self.session.execute(
                    select(func.avg(CourseGrade.percentage)).where(
                        CourseGrade.org_id == org_id,
                        CourseGrade.course_id == course.id,
                        CourseGrade.percentage.isnot(None),
                        CourseGrade.status.in_(["calculated", "released"])
                    )
                ).scalar()
            
            if course_avg:
                course_distribution.append({
                    "course_name": course.name,
                    "average": self._round(course_avg)
                })
        
        # Learners at risk (grade < 60%)
        at_risk = self.session.execute(
            select(User, CourseGrade.percentage)
            .join(CourseGrade, CourseGrade.user_id == User.id)
            .where(
                CourseGrade.course_id.in_(course_ids),
                CourseGrade.percentage < 60.0,
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
            .limit(10)
        ).all()
        
        if org_id:
            at_risk = self.session.execute(
                select(User, CourseGrade.percentage)
                .join(CourseGrade, CourseGrade.user_id == User.id)
                .where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.percentage < 60.0,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
                .limit(10)
            ).all()
        
        learners_at_risk = [
            {"full_name": user.full_name, "grade": self._round(percentage)}
            for user, percentage in at_risk
        ]
        
        # Top performers (grade >= 90%)
        top_performers = self.session.execute(
            select(User, CourseGrade.percentage)
            .join(CourseGrade, CourseGrade.user_id == User.id)
            .where(
                CourseGrade.course_id.in_(course_ids),
                CourseGrade.percentage >= 90.0,
                CourseGrade.percentage.isnot(None),
                CourseGrade.status.in_(["calculated", "released"])
            )
            .order_by(desc(CourseGrade.percentage))
            .limit(5)
        ).all()
        
        if org_id:
            top_performers = self.session.execute(
                select(User, CourseGrade.percentage)
                .join(CourseGrade, CourseGrade.user_id == User.id)
                .where(
                    CourseGrade.org_id == org_id,
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.percentage >= 90.0,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
                .order_by(desc(CourseGrade.percentage))
                .limit(5)
            ).all()
        
        top_performers_list = [
            {"full_name": user.full_name, "grade": self._round(percentage)}
            for user, percentage in top_performers
        ]
        
        # Grade trend (last 6 months)
        from datetime import datetime, timedelta
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        trend_data = []
        for i in range(6):
            month_start = six_months_ago + timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            
            month_avg = self.session.execute(
                select(func.avg(CourseGrade.percentage)).where(
                    CourseGrade.course_id.in_(course_ids),
                    CourseGrade.calculated_at >= month_start,
                    CourseGrade.calculated_at < month_end,
                    CourseGrade.percentage.isnot(None),
                    CourseGrade.status.in_(["calculated", "released"])
                )
            ).scalar()
            
            if org_id:
                month_avg = self.session.execute(
                    select(func.avg(CourseGrade.percentage)).where(
                        CourseGrade.org_id == org_id,
                        CourseGrade.course_id.in_(course_ids),
                        CourseGrade.calculated_at >= month_start,
                        CourseGrade.calculated_at < month_end,
                        CourseGrade.percentage.isnot(None),
                        CourseGrade.status.in_(["calculated", "released"])
                    )
                ).scalar()
            
            trend_data.append({
                "month": month_start.strftime("%b"),
                "average": self._round(month_avg) if month_avg else 0.0
            })
        
        # Total assessments
        total_assessments = self.session.execute(
            select(func.count(GradeItem.id)).where(
                GradeItem.course_id.in_(course_ids),
                GradeItem.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        if org_id:
            total_assessments = self.session.execute(
                select(func.count(GradeItem.id)).where(
                    GradeItem.org_id == org_id,
                    GradeItem.course_id.in_(course_ids),
                    GradeItem.deleted_at.is_(None)
                )
            ).scalar() or 0
        
        return {
            "average_grade": average_grade,
            "pass_rate": pass_rate,
            "fail_rate": fail_rate,
            "quiz_average": quiz_average,
            "assignment_average": assignment_average,
            "course_grade_distribution": course_distribution,
            "learners_at_risk": learners_at_risk,
            "top_performers": top_performers_list,
            "grade_trend": trend_data,
            "grade_summary": {
                "total_graded": total_grades,
                "total_assessments": total_assessments
            }
        }

    def get_grading_analytics_learner(self, user_id: str) -> dict[str, Any]:
        """Returns learner-specific grading analytics for Learner dashboard."""
        from app.models.gradebook import CourseGrade, GradeResult, GradeItem, GradeCategory
        
        # Get learner's course grades
        course_grades = self.session.execute(
            select(CourseGrade).where(
                CourseGrade.user_id == user_id,
                CourseGrade.percentage.isnot(None)
            )
        ).scalars().all()
        
        if not course_grades:
            return {
                "has_grades": False,
                "message": "Grade will be available after evaluation."
            }
        
        # Calculate overall statistics
        grades_list = [g.percentage for g in course_grades if g.percentage is not None]
        overall_average = self._round(sum(grades_list) / len(grades_list)) if grades_list else 0.0
        
        # Pass/fail status based on most recent or highest grade
        passed_grades = [g for g in course_grades if g.passed is True]
        overall_passed = bool(passed_grades)
        
        # Quiz average
        quiz_results = self.session.execute(
            select(GradeResult).where(
                GradeResult.user_id == user_id,
                GradeResult.source_type == "quiz_block",
                GradeResult.percentage.isnot(None),
                GradeResult.status == "graded"
            )
        ).scalars().all()
        
        quiz_scores = [r.percentage for r in quiz_results if r.percentage is not None]
        quiz_average = self._round(sum(quiz_scores) / len(quiz_scores)) if quiz_scores else 0.0
        
        # Assignment average
        assignment_results = self.session.execute(
            select(GradeResult).where(
                GradeResult.user_id == user_id,
                GradeResult.source_type == "assignment_block",
                GradeResult.percentage.isnot(None),
                GradeResult.status == "graded"
            )
        ).scalars().all()
        
        assignment_scores = [r.percentage for r in assignment_results if r.percentage is not None]
        assignment_average = self._round(sum(assignment_scores) / len(assignment_scores)) if assignment_scores else 0.0
        
        # Current percentage (most recent course grade)
        current_percentage = self._round(course_grades[0].percentage) if course_grades else 0.0
        
        # Grade summary by course
        grade_summary = []
        for grade in course_grades:
            course = self.session.execute(
                select(Course).where(Course.id == grade.course_id)
            ).scalar_one_or_none()
            
            grade_summary.append({
                "course_name": course.name if course else "Unknown Course",
                "percentage": self._round(grade.percentage),
                "display_grade": grade.display_grade,
                "passed": grade.passed,
                "status": grade.status
            })
        
        # Grade progress (trend over time)
        grade_progress = [
            {
                "course_name": gs["course_name"],
                "percentage": gs["percentage"]
            }
            for gs in grade_summary
        ]
        
        return {
            "has_grades": True,
            "final_grade": overall_average,
            "current_percentage": current_percentage,
            "quiz_average": quiz_average,
            "assignment_average": assignment_average,
            "pass_fail_status": "Pass" if overall_passed else "Fail",
            "grade_summary": grade_summary,
            "grade_progress": grade_progress,
            "total_courses_graded": len(course_grades)
        }
