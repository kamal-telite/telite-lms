"""Category-level analytics queries."""

from datetime import datetime, timedelta
from typing import Any
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
from app.services.pal_score_service import PALScoreService
from app.repositories.analytics.utils import (
    round_value,
    safe_json_list,
    iso_format,
    event_type,
    event_status,
    event_title,
)


def get_category_metrics(
    session: Session,
    category_slug: str,
    org_id: int | None = None
) -> dict[str, Any]:
    """Provides metrics for Category Admin Dashboard."""
    category_stmt = select(Category).where(
        Category.slug == category_slug,
        Category.status != "archived",
        Category.org_id == org_id
    )
    if org_id:
        category_stmt = category_stmt.where(Category.org_id == org_id)
    category = session.execute(category_stmt).scalar_one_or_none()
    if not category:
        raise ValueError("Category not found.")

    course_stmt = select(Course).where(
        Course.status != "archived",
        Course.category_slug == category_slug
    )
    learner_stmt = select(User).where(
        User.role == "learner",
        User.category_scope == category_slug
    )
    enroll_stmt = select(EnrollmentRequest).where(
        EnrollmentRequest.category_slug == category_slug,
        EnrollmentRequest.status.in_(["pending", "flagged"])
    )
    verification_stmt = select(func.count(PendingVerification.id)).where(
        PendingVerification.status == "pending"
    )
    
    if org_id:
        course_stmt = course_stmt.where(Course.org_id == org_id)
        learner_stmt = learner_stmt.where(User.org_id == org_id)
        enroll_stmt = enroll_stmt.where(EnrollmentRequest.org_id == org_id)
        verification_stmt = verification_stmt.where(PendingVerification.organization_id == org_id)
        
    courses = session.execute(course_stmt).scalars().all()
    learners = session.execute(learner_stmt).scalars().all()
    if org_id:
        pal_service = PALScoreService(session)
        for learner in learners:
            pal_service.recompute_user(learner.id, org_id)
    pending_requests = session.execute(enroll_stmt).scalars().all()
    pending_verifications = session.execute(verification_stmt).scalar() or 0
    course_ids = [course.id for course in courses]
    learner_ids = [learner.id for learner in learners]

    module_rows = []
    progress_rows = []
    module_progress_rows = []
    latest_events = []
    if course_ids:
        module_stmt = (
            select(CourseModule)
            .where(
                CourseModule.course_id.in_(course_ids),
                CourseModule.deleted_at.is_(None)
            )
            .order_by(
                CourseModule.course_id,
                CourseModule.section,
                CourseModule.sort_order,
                CourseModule.id
            )
        )
        progress_stmt = select(CourseProgress).where(
            CourseProgress.course_id.in_(course_ids)
        )
        module_progress_stmt = (
            select(ModuleProgress)
            .join(CourseModule, CourseModule.id == ModuleProgress.module_id)
            .where(
                CourseModule.course_id.in_(course_ids),
                CourseModule.deleted_at.is_(None)
            )
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
        module_rows = session.execute(module_stmt).scalars().all()
        progress_rows = session.execute(progress_stmt).scalars().all()
        module_progress_rows = session.execute(module_progress_stmt).scalars().all()
        latest_events = session.execute(event_stmt).scalars().all()

    modules_by_course: dict[str, list[CourseModule]] = {}
    module_title_by_id: dict[int, str] = {}
    for module in module_rows:
        modules_by_course.setdefault(module.course_id, []).append(module)
        module_title_by_id[module.id] = module.title

    normalized_by_user_course = {(row.user_id, row.course_id): row for row in progress_rows}
    legacy_by_user_course: dict[tuple[str, str], dict[str, Any]] = {}
    for learner in learners:
        for item in safe_json_list(learner.course_progress_json):
            course_id = item.get("course_id")
            if course_id:
                legacy_by_user_course[(learner.id, course_id)] = item

    all_progress_keys = set(normalized_by_user_course) | set(legacy_by_user_course)
    progress_keys_by_course: dict[str, set[tuple[str, str]]] = {
        course.id: set() for course in courses
    }
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
                "progress": round_value(row.completion_percentage, 0),
                "completion_percentage": round_value(row.completion_percentage, 0),
                "time_spent_seconds": row.time_spent_seconds,
                "current_lesson": row.status.replace("_", " "),
                "last_active": row.last_viewed_at.isoformat() if row.last_viewed_at else None,
            }
        legacy = legacy_by_user_course.get((user_id, course_id), {})
        return {
            "course_id": course_id,
            "status": legacy.get("status", "not_started"),
            "progress": round_value(legacy.get("progress", 0), 0),
            "completion_percentage": round_value(legacy.get("progress", 0), 0),
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
        enrolled_pal = [
            learner_by_id[user_id].pal_score
            for user_id in enrolled_user_ids
            if user_id in learner_by_id
        ]
        module_titles = [module.title for module in modules_by_course.get(course.id, [])]
        course_rows.append({
            "id": course.id,
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
            "created_at": iso_format(course.created_at),
            "module_count": len(module_titles),
            "modules": module_titles,
            "enrolled_count": enrolled_count,
            "completion_count": completed_count,
            "completion_rate": round_value(completion_rate),
            "completion_pct": round_value(completion_rate),
            "avg_pal_score": round_value(
                sum(enrolled_pal) / len(enrolled_pal), 1
            ) if enrolled_pal else round_value(course.avg_quiz_score),
        })

    learner_rows = []
    completion_values = []
    time_values = []
    for learner in learners:
        keys = [
            key for key in all_progress_keys
            if key[0] == learner.id and key[1] in course_by_id
        ]
        items = [
            progress_item(learner.id, course_id)
            for _, course_id in sorted(keys, key=lambda value: value[1])
        ]
        completed = len([
            item for item in items
            if item["status"] == "completed" or item["completion_percentage"] >= 100
        ])
        total_courses = len(items) or learner.total_courses or len(courses)
        avg_completion = (
            sum(item["completion_percentage"] for item in items) / len(items)
            if items else learner.pal_completion_pct
        )
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
            "created_at": iso_format(learner.created_at),
            "enrollment_type": learner.enrollment_type or "manual",
            "avatar_gradient": [learner.gradient_start, learner.gradient_end],
            "current_course_id": learner.current_course_id,
            "total_courses": total_courses,
            "courses_completed": completed,
            "course_progress": items,
            "pal_score": round_value(learner.pal_score),
            "pal_completion_pct": round_value(avg_completion),
            "pal_quiz_avg": round_value(learner.pal_quiz_avg),
            "pal_time_spent_hours": round_value(
                total_time_seconds / 3600 if total_time_seconds else learner.pal_time_spent_hours
            ),
            "pal_task_completion_pct": round_value(learner.pal_task_completion_pct),
            "last_active": max(
                (item["last_active"] for item in items if item["last_active"]),
                default=None
            ),
        })

    active_module_count = len([
        row for row in module_progress_rows
        if row.status in {"in_progress", "completed"}
    ])
    avg_pal_score = (
        sum(row["pal_score"] for row in learner_rows) / len(learner_rows)
        if learner_rows else 0.0
    )
    avg_completion = (
        sum(completion_values) / len(completion_values)
        if completion_values else 0.0
    )
    avg_time_hours = sum(time_values) / len(time_values) if time_values else 0.0

    tasks = session.execute(
        select(Task).where(Task.category_slug == category_slug)
    ).scalars().all()
    if org_id:
        tasks = [task for task in tasks if task.org_id == org_id]

    activity = []
    for event in latest_events:
        learner_name = (
            learner_by_id.get(event.user_id).full_name
            if event.user_id in learner_by_id else "A learner"
        )
        course_name = (
            course_by_id.get(event.course_id).name
            if event.course_id in course_by_id else None
        )
        activity.append({
            "id": f"learner-event-{event.id}",
            "type": event_type(event.event_type),
            "status": event_status(event.event_type),
            "title": event_title(
                event.event_type,
                learner_name,
                course_name,
                module_title_by_id.get(event.module_id)
            ),
            "message": event_title(
                event.event_type,
                learner_name,
                course_name,
                module_title_by_id.get(event.module_id)
            ),
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
        "created_at": iso_format(category.created_at),
    }

    return {
        "category": category_payload,
        "kpis": {
            "total_courses": len(course_rows),
            "active_learners": len(learner_rows),
            "pending_enrollment": len(pending_requests),
            "pending_verifications": pending_verifications,
            "modules_started": active_module_count,
            "avg_pal_score": round_value(avg_pal_score),
            "avg_completion": round_value(avg_completion),
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
                "created_at": iso_format(task.created_at),
            }
            for task in tasks
        ],
        "activity": activity,
        "pal": {
            "summary": {
                "avg_completion": round_value(avg_completion),
                "avg_quiz_score": round_value(
                    sum(row["pal_quiz_avg"] for row in learner_rows) / len(learner_rows), 1
                ) if learner_rows else 0.0,
                "avg_time_hours": round_value(avg_time_hours),
            },
            "leaderboard": pal_leaderboard,
            "chart": [
                {"name": row["full_name"].split()[0], "score": row["pal_score"]}
                for row in pal_leaderboard
            ],
        },
        "leaderboard": pal_leaderboard[:4],
    }
