"""
Celery tasks for async Moodle synchronisation — Phase 5.

Each task:
  1. Calls the Moodle API
  2. Updates the sync status in moodle_sync_logs
  3. Updates the moodle_id on the relevant Telite record
  4. Retries with exponential backoff on failure
  5. Moves to dead-letter after max retries

Retry schedule:
  Attempt 1: immediate
  Attempt 2: 30 seconds
  Attempt 3: 5 minutes
  Attempt 4: 30 minutes
  Attempt 5: 2 hours
  → Dead letter (manual review required)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger("telite.workers.moodle")

# Retry countdown in seconds: 30s, 5m, 30m, 2h
RETRY_COUNTDOWNS = [30, 300, 1800, 7200]
MAX_RETRIES = len(RETRY_COUNTDOWNS)


def _retry_countdown(retries: int) -> int:
    """Return the countdown in seconds for the next retry attempt."""
    if retries < len(RETRY_COUNTDOWNS):
        return RETRY_COUNTDOWNS[retries]
    return RETRY_COUNTDOWNS[-1]


def _write_sync_log(
    org_id: int,
    event_type: str,
    status: str,
    message: str,
    duration_ms: int = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write a sync log entry to moodle_sync_logs."""
    try:
        import json
        from app.services.store import get_conn, now_local
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO moodle_sync_logs
                    (org_id, event_type, status, message, duration_ms, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    org_id,
                    event_type,
                    status,
                    message,
                    duration_ms,
                    json.dumps(metadata) if metadata else None,
                    now_local(),
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.error("Failed to write sync log: %s", exc)


def _update_moodle_id(table: str, record_id: str, moodle_id: int) -> None:
    """Update the moodle_id on a Telite record after successful sync."""
    try:
        from app.services.store import get_conn
        col = "moodle_id" if table == "users" else "moodle_course_id" if table == "courses" else "moodle_category_id"
        with get_conn() as conn:
            conn.execute(
                f"UPDATE {table} SET {col} = ? WHERE id = ?",
                (moodle_id, record_id),
            )
            conn.commit()
    except Exception as exc:
        logger.error("Failed to update moodle_id on %s %s: %s", table, record_id, exc)


# ── User sync tasks ───────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_user_created",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_user_created(
    self: Task,
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
) -> dict[str, Any]:
    """Create a user in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_create_user
    from app.core.password_utils import get_default_learner_password

    start = time.time()
    event_type = "user.created"

    try:
        parts = full_name.strip().split(" ", 1)
        firstname = parts[0]
        lastname = parts[1] if len(parts) > 1 else "."

        custom_fields: dict[str, str] = {}
        if program:
            custom_fields["program"] = program
        if branch:
            custom_fields["branch"] = branch
        if id_number:
            custom_fields["id_number"] = id_number

        result = moodle_create_user(
            username=username,
            password=password or get_default_learner_password(),
            firstname=firstname,
            lastname=lastname,
            email=email,
            custom_fields=custom_fields or None,
        )

        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            moodle_user_id = result["user_id"]
            _update_moodle_id("users", user_id, moodle_user_id)
            _write_sync_log(
                org_id, event_type, "synced",
                f"User {username} synced to Moodle (id={moodle_user_id})",
                duration_ms,
                {"user_id": user_id, "moodle_user_id": moodle_user_id},
            )
            logger.info("User %s synced to Moodle id=%d", username, moodle_user_id)
            return {"status": "synced", "moodle_user_id": moodle_user_id}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        retries = self.request.retries
        countdown = _retry_countdown(retries)

        if retries >= MAX_RETRIES:
            _write_sync_log(
                org_id, event_type, "dead_letter",
                f"User {username} sync failed after {MAX_RETRIES} retries: {exc}",
                duration_ms,
                {"user_id": user_id, "error": str(exc)},
            )
            logger.error("User %s sync dead-lettered after %d retries: %s", username, MAX_RETRIES, exc)
            return {"status": "dead_letter", "error": str(exc)}

        _write_sync_log(
            org_id, event_type, "retrying",
            f"User {username} sync failed (attempt {retries + 1}), retrying in {countdown}s: {exc}",
            duration_ms,
        )
        logger.warning("User %s sync failed (attempt %d), retrying in %ds: %s", username, retries + 1, countdown, exc)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_user_suspended",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_user_suspended(
    self: Task,
    *,
    user_id: str,
    moodle_user_id: int,
    org_id: int,
) -> dict[str, Any]:
    """Suspend a user in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_suspend_user

    start = time.time()
    event_type = "user.suspended"

    try:
        result = moodle_suspend_user(moodle_user_id)
        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            _write_sync_log(
                org_id, event_type, "synced",
                f"User {user_id} suspended in Moodle (moodle_id={moodle_user_id})",
                duration_ms,
            )
            return {"status": "synced"}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        retries = self.request.retries
        countdown = _retry_countdown(retries)

        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"User suspend dead-lettered: {exc}", duration_ms)
            return {"status": "dead_letter", "error": str(exc)}

        raise self.retry(exc=exc, countdown=countdown)


# ── Course sync tasks ─────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_course_created",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_course_created(
    self: Task,
    *,
    course_id: str,
    name: str,
    category_slug: str,
    org_id: int,
    moodle_category_id: int | None = None,
) -> dict[str, Any]:
    """Create a course in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_create_course

    start = time.time()
    event_type = "course.created"

    try:
        # Resolve moodle_category_id if not provided
        if not moodle_category_id:
            from app.services.store import get_conn
            with get_conn() as conn:
                row = conn.execute(
                    "SELECT moodle_category_id FROM categories WHERE slug = ? LIMIT 1",
                    (category_slug,),
                ).fetchone()
                if row:
                    moodle_category_id = row["moodle_category_id"] if isinstance(row, dict) else row[0]

        if not moodle_category_id:
            raise RuntimeError(f"No moodle_category_id for category_slug={category_slug}")

        result = moodle_create_course(name=name, category_id=moodle_category_id)
        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            moodle_course_id = result["course_id"]
            _update_moodle_id("courses", course_id, moodle_course_id)
            _write_sync_log(
                org_id, event_type, "synced",
                f"Course '{name}' synced to Moodle (id={moodle_course_id})",
                duration_ms,
                {"course_id": course_id, "moodle_course_id": moodle_course_id},
            )
            return {"status": "synced", "moodle_course_id": moodle_course_id}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        retries = self.request.retries
        countdown = _retry_countdown(retries)

        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Course '{name}' sync dead-lettered: {exc}", duration_ms)
            return {"status": "dead_letter", "error": str(exc)}

        _write_sync_log(org_id, event_type, "retrying",
                        f"Course '{name}' sync retrying in {countdown}s: {exc}", duration_ms)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_course_archived",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_course_archived(
    self: Task,
    *,
    course_id: str,
    moodle_course_id: int,
    org_id: int,
) -> dict[str, Any]:
    """Archive/delete a course in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_delete_courses

    start = time.time()
    event_type = "course.archived"

    try:
        result = moodle_delete_courses([moodle_course_id])
        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            _write_sync_log(org_id, event_type, "synced",
                            f"Course {course_id} archived in Moodle", duration_ms)
            return {"status": "synced"}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        retries = self.request.retries
        countdown = _retry_countdown(retries)
        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Course archive dead-lettered: {exc}", 0)
            return {"status": "dead_letter", "error": str(exc)}
        raise self.retry(exc=exc, countdown=countdown)


# ── Enrollment sync tasks ─────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_enrollment_approved",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_enrollment_approved(
    self: Task,
    *,
    enrollment_id: str,
    user_id: str,
    course_id: str,
    org_id: int,
    moodle_user_id: int | None = None,
    moodle_course_id: int | None = None,
) -> dict[str, Any]:
    """Enrol a user in a Moodle course asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_enrol_student
    from app.services.store import get_conn

    start = time.time()
    event_type = "enrollment.approved"

    try:
        # Resolve Moodle IDs if not provided
        with get_conn() as conn:
            if not moodle_user_id:
                row = conn.execute(
                    "SELECT moodle_id FROM users WHERE id = ? LIMIT 1", (user_id,)
                ).fetchone()
                if row:
                    moodle_user_id = row["moodle_id"] if isinstance(row, dict) else row[0]

            if not moodle_course_id:
                row = conn.execute(
                    "SELECT moodle_course_id FROM courses WHERE id = ? LIMIT 1", (course_id,)
                ).fetchone()
                if row:
                    moodle_course_id = row["moodle_course_id"] if isinstance(row, dict) else row[0]

        if not moodle_user_id:
            raise RuntimeError(f"No moodle_id for user {user_id} — user may not be synced yet")
        if not moodle_course_id:
            raise RuntimeError(f"No moodle_course_id for course {course_id} — course may not be synced yet")

        success = moodle_enrol_student(moodle_user_id, moodle_course_id)
        duration_ms = int((time.time() - start) * 1000)

        if success:
            _write_sync_log(
                org_id, event_type, "synced",
                f"Enrollment {enrollment_id}: user {user_id} enrolled in course {course_id}",
                duration_ms,
                {"enrollment_id": enrollment_id, "moodle_user_id": moodle_user_id, "moodle_course_id": moodle_course_id},
            )
            return {"status": "synced"}

        raise RuntimeError("moodle_enrol_student returned False")

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        retries = self.request.retries
        countdown = _retry_countdown(retries)

        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Enrollment {enrollment_id} dead-lettered: {exc}", duration_ms)
            return {"status": "dead_letter", "error": str(exc)}

        _write_sync_log(org_id, event_type, "retrying",
                        f"Enrollment {enrollment_id} retrying in {countdown}s: {exc}", duration_ms)
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_enrollment_revoked",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_enrollment_revoked(
    self: Task,
    *,
    enrollment_id: str,
    user_id: str,
    course_id: str,
    org_id: int,
    moodle_user_id: int | None = None,
    moodle_course_id: int | None = None,
) -> dict[str, Any]:
    """Unenrol a user from a Moodle course asynchronously."""
    import time
    from app.services.store import get_conn

    start = time.time()
    event_type = "enrollment.revoked"

    try:
        with get_conn() as conn:
            if not moodle_user_id:
                row = conn.execute("SELECT moodle_id FROM users WHERE id = ? LIMIT 1", (user_id,)).fetchone()
                if row:
                    moodle_user_id = row["moodle_id"] if isinstance(row, dict) else row[0]
            if not moodle_course_id:
                row = conn.execute("SELECT moodle_course_id FROM courses WHERE id = ? LIMIT 1", (course_id,)).fetchone()
                if row:
                    moodle_course_id = row["moodle_course_id"] if isinstance(row, dict) else row[0]

        if not moodle_user_id or not moodle_course_id:
            # Nothing to unenrol — log and skip
            _write_sync_log(org_id, event_type, "skipped",
                            f"Enrollment {enrollment_id} revoke skipped — no Moodle IDs", 0)
            return {"status": "skipped"}

        # Moodle unenrol via manual enrolment plugin
        from app.integrations.moodle_bridge import _call
        result = _call(
            "enrol_manual_unenrol_users",
            **{
                "enrolments[0][userid]": str(moodle_user_id),
                "enrolments[0][courseid]": str(moodle_course_id),
            },
        )
        duration_ms = int((time.time() - start) * 1000)

        if result.get("error") is None:
            _write_sync_log(org_id, event_type, "synced",
                            f"Enrollment {enrollment_id} revoked in Moodle", duration_ms)
            return {"status": "synced"}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        retries = self.request.retries
        countdown = _retry_countdown(retries)
        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Enrollment revoke dead-lettered: {exc}", 0)
            return {"status": "dead_letter", "error": str(exc)}
        raise self.retry(exc=exc, countdown=countdown)


# ── Category sync tasks ───────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_category_archived",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_category_archived(
    self: Task,
    *,
    category_id: str,
    moodle_category_id: int,
    org_id: int,
) -> dict[str, Any]:
    """Archive/delete a category in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_delete_category

    start = time.time()
    event_type = "category.archived"

    try:
        result = moodle_delete_category(moodle_category_id)
        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            _write_sync_log(org_id, event_type, "synced",
                            f"Category {category_id} archived in Moodle", duration_ms)
            return {"status": "synced"}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        retries = self.request.retries
        countdown = _retry_countdown(retries)
        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Category archive dead-lettered: {exc}", 0)
            return {"status": "dead_letter", "error": str(exc)}
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.moodle_tasks.sync_category_created",
    max_retries=MAX_RETRIES,
    queue="moodle_sync",
)
def sync_category_created(
    self: Task,
    *,
    category_id: str,
    name: str,
    slug: str,
    org_id: int,
    description: str = "",
) -> dict[str, Any]:
    """Create a category in Moodle asynchronously."""
    import time
    from app.integrations.moodle_bridge import moodle_create_category

    start = time.time()
    event_type = "category.created"

    try:
        result = moodle_create_category(name=name, slug=slug, description=description)
        duration_ms = int((time.time() - start) * 1000)

        if result.get("success"):
            moodle_cat_id = result["category_id"]
            _update_moodle_id("categories", category_id, moodle_cat_id)
            _write_sync_log(
                org_id, event_type, "synced",
                f"Category '{name}' synced to Moodle (id={moodle_cat_id})",
                duration_ms,
                {"category_id": category_id, "moodle_category_id": moodle_cat_id},
            )
            return {"status": "synced", "moodle_category_id": moodle_cat_id}

        raise RuntimeError(result.get("error", "Unknown Moodle error"))

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        retries = self.request.retries
        countdown = _retry_countdown(retries)

        if retries >= MAX_RETRIES:
            _write_sync_log(org_id, event_type, "dead_letter",
                            f"Category '{name}' sync dead-lettered: {exc}", duration_ms)
            return {"status": "dead_letter", "error": str(exc)}

        _write_sync_log(org_id, event_type, "retrying",
                        f"Category '{name}' sync retrying in {countdown}s: {exc}", duration_ms)
        raise self.retry(exc=exc, countdown=countdown)
