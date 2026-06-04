"""
Moodle event publisher — Phase 5.

FastAPI routes call publish_*() functions instead of calling Moodle directly.
Events are placed on the Redis queue and processed asynchronously by Celery.

This decouples FastAPI response time from Moodle API latency.
FastAPI returns 200 immediately; Moodle sync happens in the background.

Event types:
  user.created          → create Moodle user
  user.suspended        → suspend Moodle user
  course.created        → create Moodle course
  course.archived       → hide/delete Moodle course
  enrollment.approved   → enrol user in Moodle course
  enrollment.revoked    → unenrol user from Moodle course
  category.created      → create Moodle category
  category.archived     → delete Moodle category
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("telite.moodle.events")


def _dispatch(task_name: str, payload: dict[str, Any]) -> str | None:
    """
    Dispatch a Moodle sync task to the Celery queue.

    Returns the Celery task ID, or None if dispatch failed.
    Failures are logged but never raise — FastAPI must not fail
    because of a queue dispatch error.
    """
    try:
        from app.workers.celery_app import celery_app
        result = celery_app.send_task(
            task_name,
            kwargs=payload,
            queue="moodle_sync",
        )
        logger.info(
            "Dispatched %s task_id=%s payload_keys=%s",
            task_name,
            result.id,
            list(payload.keys()),
        )
        return result.id
    except Exception as exc:
        logger.error(
            "Failed to dispatch %s: %s — Moodle sync will be deferred to reconciliation",
            task_name,
            exc,
        )
        return None


# ── Public event publishers ───────────────────────────────────────────────────

def publish_user_created(
    *,
    user_id: str,
    username: str,
    email: str,
    full_name: str,
    org_id: int,
    password: str | None = None,
    program: str | None = None,
    branch: str | None = None,
    id_number: str | None = None,
) -> str | None:
    """Publish event to create a user in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_user_created",
        {
            "user_id": user_id,
            "username": username,
            "email": email,
            "full_name": full_name,
            "org_id": org_id,
            "password": password,
            "program": program,
            "branch": branch,
            "id_number": id_number,
        },
    )


def publish_user_suspended(
    *,
    user_id: str,
    moodle_user_id: int,
    org_id: int,
) -> str | None:
    """Publish event to suspend a user in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_user_suspended",
        {
            "user_id": user_id,
            "moodle_user_id": moodle_user_id,
            "org_id": org_id,
        },
    )


def publish_course_created(
    *,
    course_id: str,
    name: str,
    category_slug: str,
    org_id: int,
    moodle_category_id: int | None = None,
) -> str | None:
    """Publish event to create a course in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_course_created",
        {
            "course_id": course_id,
            "name": name,
            "category_slug": category_slug,
            "org_id": org_id,
            "moodle_category_id": moodle_category_id,
        },
    )


def publish_course_archived(
    *,
    course_id: str,
    moodle_course_id: int,
    org_id: int,
) -> str | None:
    """Publish event to archive/hide a course in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_course_archived",
        {
            "course_id": course_id,
            "moodle_course_id": moodle_course_id,
            "org_id": org_id,
        },
    )


def publish_enrollment_approved(
    *,
    enrollment_id: str,
    user_id: str,
    course_id: str,
    org_id: int,
    moodle_user_id: int | None = None,
    moodle_course_id: int | None = None,
) -> str | None:
    """Publish event to enrol a user in a Moodle course."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_enrollment_approved",
        {
            "enrollment_id": enrollment_id,
            "user_id": user_id,
            "course_id": course_id,
            "org_id": org_id,
            "moodle_user_id": moodle_user_id,
            "moodle_course_id": moodle_course_id,
        },
    )


def publish_enrollment_revoked(
    *,
    enrollment_id: str,
    user_id: str,
    course_id: str,
    org_id: int,
    moodle_user_id: int | None = None,
    moodle_course_id: int | None = None,
) -> str | None:
    """Publish event to unenrol a user from a Moodle course."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_enrollment_revoked",
        {
            "enrollment_id": enrollment_id,
            "user_id": user_id,
            "course_id": course_id,
            "org_id": org_id,
            "moodle_user_id": moodle_user_id,
            "moodle_course_id": moodle_course_id,
        },
    )


def publish_category_created(
    *,
    category_id: str,
    name: str,
    slug: str,
    org_id: int,
    description: str = "",
) -> str | None:
    """Publish event to create a category in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_category_created",
        {
            "category_id": category_id,
            "name": name,
            "slug": slug,
            "org_id": org_id,
            "description": description,
        },
    )


def publish_category_archived(
    *,
    category_id: str,
    moodle_category_id: int,
    org_id: int,
) -> str | None:
    """Publish event to archive/delete a category in Moodle."""
    return _dispatch(
        "app.workers.moodle_tasks.sync_category_archived",
        {
            "category_id": category_id,
            "moodle_category_id": moodle_category_id,
            "org_id": org_id,
        },
    )


# ── Compatibility shim for management.py ─────────────────────────────────────

def publish_moodle_event(
    record: dict[str, Any],
    event_type: str,
    *,
    org_id: int,
) -> str | None:
    """
    Generic event dispatcher — compatibility shim for management.py.

    Routes to the appropriate typed publisher based on event_type.
    New code should use the typed publish_*() functions directly.
    """
    try:
        if event_type == "user.created":
            return publish_user_created(
                user_id=record.get("id", ""),
                username=record.get("username", ""),
                email=record.get("email", ""),
                full_name=record.get("full_name", ""),
                org_id=org_id,
                program=record.get("program"),
                branch=record.get("branch"),
                id_number=record.get("id_number"),
            )

        if event_type == "user.suspended":
            moodle_id = record.get("moodle_user_id") or record.get("moodle_id")
            if not moodle_id:
                logger.warning("publish_moodle_event user.suspended: no moodle_id in record")
                return None
            return publish_user_suspended(
                user_id=record.get("id", ""),
                moodle_user_id=int(moodle_id),
                org_id=org_id,
            )

        if event_type == "course.created":
            return publish_course_created(
                course_id=record.get("id", ""),
                name=record.get("name", ""),
                category_slug=record.get("category_slug", ""),
                org_id=org_id,
                moodle_category_id=record.get("moodle_category_id"),
            )

        if event_type == "course.archived":
            moodle_id = record.get("moodle_course_id")
            if not moodle_id:
                return None
            return publish_course_archived(
                course_id=record.get("id", ""),
                moodle_course_id=int(moodle_id),
                org_id=org_id,
            )

        if event_type == "category.created":
            return publish_category_created(
                category_id=record.get("id", ""),
                name=record.get("name", ""),
                slug=record.get("slug", ""),
                org_id=org_id,
                description=record.get("description", ""),
            )

        if event_type == "category.archived":
            moodle_id = record.get("moodle_category_id")
            if not moodle_id:
                return None
            return publish_category_archived(
                category_id=record.get("id", ""),
                moodle_category_id=int(moodle_id),
                org_id=org_id,
            )

        if event_type == "enrollment.approved":
            return publish_enrollment_approved(
                enrollment_id=record.get("id", ""),
                user_id=record.get("user_id", ""),
                course_id=record.get("course_id", ""),
                org_id=org_id,
                moodle_user_id=record.get("moodle_user_id"),
                moodle_course_id=record.get("moodle_course_id"),
            )

        logger.warning("publish_moodle_event: unknown event_type=%s", event_type)
        return None

    except Exception as exc:
        logger.error("publish_moodle_event failed for %s: %s", event_type, exc)
        return None


# ── Reconciliation event publisher ────────────────────────────────────────────


def publish_reconciliation_event(
    org_id: int,
    *,
    actor_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Dispatch a reconciliation task for a specific organisation.

    Used by platform.py for manual sync triggers.
    Routes to the reconcile_org Celery task on the 'reconcile' queue.

    Returns dispatch metadata dict or None on failure.
    """
    try:
        from app.workers.celery_app import celery_app
        result = celery_app.send_task(
            "app.workers.reconciliation.reconcile_org",
            kwargs={"org_id": org_id},
            queue="reconcile",
        )
        logger.info(
            "Dispatched reconciliation for org_id=%d actor=%s task_id=%s",
            org_id,
            actor_id or "-",
            result.id,
        )
        return {
            "task_id": result.id,
            "org_id": org_id,
            "status": "dispatched",
            "actor_id": actor_id,
        }
    except Exception as exc:
        logger.error(
            "Failed to dispatch reconciliation for org_id=%d: %s",
            org_id,
            exc,
        )
        return None

