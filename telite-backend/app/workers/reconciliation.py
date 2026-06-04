"""
Moodle reconciliation tasks — Phase 5.

Nightly jobs that detect and fix drift between Telite DB and Moodle.

Two reconciliation modes:
  1. Quick reconciliation (reconcile_org) — checks Telite DB for missing
     Moodle IDs and re-dispatches sync events. Fast, no Moodle API calls.
  2. Full drift comparison (build_drift_report) — queries live Moodle read
     APIs to compare every user, course, enrollment, and category. Produces
     a structured DriftReport stored in moodle_sync_logs.

Drift scenarios detected by full comparison:
  1. User exists in Telite but not in Moodle (sync failed / deleted upstream)
  2. User exists in Moodle but not in Telite (orphan)
  3. Course mismatches between systems
  4. Enrollment discrepancies (approved but not enrolled, or enrolled without approval)
  5. Category structure drift
  6. Dead-letter events that need retry

These jobs run via Celery Beat on a schedule defined in celery_app.py.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger("telite.workers.reconciliation")


@celery_app.task(
    name="app.workers.reconciliation.reconcile_all_orgs",
    queue="reconcile",
)
def reconcile_all_orgs() -> dict[str, Any]:
    """
    Nightly reconciliation — check all orgs for Telite/Moodle drift.
    Dispatches individual reconcile tasks per org.
    """
    from app.services.store import get_conn

    logger.info("Starting nightly Moodle reconciliation for all orgs")

    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id FROM organizations WHERE status = 'active'"
            ).fetchall()
            org_ids = [r["id"] if isinstance(r, dict) else r[0] for r in rows]

        dispatched = 0
        for org_id in org_ids:
            reconcile_org.delay(org_id=org_id)
            dispatched += 1

        logger.info("Reconciliation dispatched for %d orgs", dispatched)
        return {"status": "dispatched", "orgs": dispatched}

    except Exception as exc:
        logger.error("Reconciliation dispatch failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@celery_app.task(
    bind=True,
    name="app.workers.reconciliation.reconcile_org",
    queue="reconcile",
    max_retries=2,
)
def reconcile_org(self, *, org_id: int) -> dict[str, Any]:
    """
    Reconcile a single organisation's Telite data with Moodle.

    Quick mode: checks Telite DB for NULL moodle_ids and re-dispatches.
    Does NOT call Moodle APIs — use build_drift_report for full comparison.
    """
    from app.services.store import get_conn
    from app.integrations.moodle_events import (
        publish_user_created,
        publish_course_created,
        publish_enrollment_approved,
    )

    logger.info("Reconciling org_id=%d", org_id)
    fixed = {"users": 0, "courses": 0, "enrollments": 0}

    try:
        with get_conn() as conn:
            # ── 1. Users without moodle_id ────────────────────────────────
            unsynced_users = conn.execute(
                """
                SELECT id, username, email, full_name
                FROM users
                WHERE org_id = ? AND moodle_id IS NULL AND is_active = 1
                  AND role = 'learner'
                LIMIT 50
                """,
                (org_id,),
            ).fetchall()

            for row in unsynced_users:
                r = dict(row) if not isinstance(row, dict) else row
                publish_user_created(
                    user_id=r["id"],
                    username=r["username"],
                    email=r["email"],
                    full_name=r["full_name"],
                    org_id=org_id,
                )
                fixed["users"] += 1

            # ── 2. Courses without moodle_course_id ───────────────────────
            unsynced_courses = conn.execute(
                """
                SELECT id, name, category_slug
                FROM courses
                WHERE org_id = ? AND moodle_course_id IS NULL AND status = 'active'
                LIMIT 50
                """,
                (org_id,),
            ).fetchall()

            for row in unsynced_courses:
                r = dict(row) if not isinstance(row, dict) else row
                publish_course_created(
                    course_id=r["id"],
                    name=r["name"],
                    category_slug=r["category_slug"],
                    org_id=org_id,
                )
                fixed["courses"] += 1

            # ── 3. Approved enrollments where user/course not synced ───────
            unsynced_enrollments = conn.execute(
                """
                SELECT er.id, er.email, er.category_slug,
                       u.id AS user_id, u.moodle_id,
                       c.id AS course_id, c.moodle_course_id
                FROM enrollment_requests er
                JOIN users u ON u.email = er.email AND u.org_id = er.org_id
                JOIN courses c ON c.category_slug = er.category_slug AND c.org_id = er.org_id
                WHERE er.org_id = ? AND er.status = 'approved'
                  AND (u.moodle_id IS NULL OR c.moodle_course_id IS NULL)
                LIMIT 50
                """,
                (org_id,),
            ).fetchall()

            for row in unsynced_enrollments:
                r = dict(row) if not isinstance(row, dict) else row
                publish_enrollment_approved(
                    enrollment_id=r["id"],
                    user_id=r["user_id"],
                    course_id=r["course_id"],
                    org_id=org_id,
                    moodle_user_id=r.get("moodle_id"),
                    moodle_course_id=r.get("moodle_course_id"),
                )
                fixed["enrollments"] += 1

        # Write reconciliation log
        from app.services.store import get_conn as _gc, now_local
        with _gc() as conn:
            conn.execute(
                """
                INSERT INTO moodle_sync_logs
                    (org_id, event_type, status, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    org_id,
                    "reconciliation",
                    "completed",
                    f"Reconciliation: {fixed['users']} users, {fixed['courses']} courses, "
                    f"{fixed['enrollments']} enrollments re-dispatched",
                    now_local(),
                ),
            )
            conn.commit()

        logger.info("Reconciliation org_id=%d complete: %s", org_id, fixed)
        return {"status": "completed", "org_id": org_id, "fixed": fixed}

    except Exception as exc:
        logger.error("Reconciliation failed for org_id=%d: %s", org_id, exc)
        raise self.retry(exc=exc, countdown=300)


# ── Full drift comparison (Phase 5 completion) ───────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.reconciliation.build_drift_report",
    queue="reconcile",
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def build_drift_report(self, *, org_id: int, auto_fix: bool = False) -> dict[str, Any]:
    """
    Full drift comparison: query live Moodle read APIs and compare
    against Telite DB state for a specific organisation.

    This is the "drift comparison against live Moodle read APIs" feature.

    Args:
        org_id: Organisation ID to check
        auto_fix: If True, re-dispatch sync events for auto-fixable drift items

    Returns:
        DriftReport as dict
    """
    from app.services.store import get_conn, now_local
    from app.integrations.moodle_bridge import (
        moodle_get_users,
        moodle_get_all_courses,
        moodle_get_categories,
        moodle_get_enrolled_users,
        moodle_get_courses_in_category,
    )
    from app.workers.drift_report import (
        DriftReport,
        compare_users,
        compare_courses,
        compare_enrollments,
        compare_categories,
    )

    logger.info("Building drift report for org_id=%d auto_fix=%s", org_id, auto_fix)
    report = DriftReport(org_id=org_id)

    try:
        # ── Fetch Telite data ─────────────────────────────────────────────
        with get_conn() as conn:
            # Users
            telite_users = conn.execute(
                """
                SELECT id, username, email, full_name, moodle_id
                FROM users
                WHERE org_id = ? AND is_active = 1 AND role = 'learner'
                """,
                (org_id,),
            ).fetchall()
            telite_users = [dict(r) if not isinstance(r, dict) else r for r in telite_users]

            # Courses
            telite_courses = conn.execute(
                """
                SELECT id, name, category_slug, moodle_course_id
                FROM courses
                WHERE org_id = ? AND status = 'active'
                """,
                (org_id,),
            ).fetchall()
            telite_courses = [dict(r) if not isinstance(r, dict) else r for r in telite_courses]

            # Categories
            telite_categories = conn.execute(
                """
                SELECT id, name, slug, moodle_category_id
                FROM categories
                WHERE org_id = ?
                """,
                (org_id,),
            ).fetchall()
            telite_categories = [dict(r) if not isinstance(r, dict) else r for r in telite_categories]

            # Moodle tenant mapping
            tenant_row = conn.execute(
                "SELECT moodle_cat_id FROM moodle_tenants WHERE org_id = ?",
                (org_id,),
            ).fetchone()
            moodle_parent_cat_id = None
            if tenant_row:
                moodle_parent_cat_id = (
                    tenant_row["moodle_cat_id"]
                    if isinstance(tenant_row, dict)
                    else tenant_row[0]
                )

        # ── Fetch Moodle data ─────────────────────────────────────────────
        moodle_users = moodle_get_users()
        moodle_all_courses = moodle_get_all_courses()
        moodle_categories = moodle_get_categories()

        # Filter Moodle courses to this org's category tree if we know the parent
        if moodle_parent_cat_id:
            org_category_ids = _get_category_subtree_ids(
                moodle_categories, int(moodle_parent_cat_id)
            )
            moodle_courses = [
                c for c in moodle_all_courses
                if int(c.get("categoryid", 0)) in org_category_ids
            ]
        else:
            moodle_courses = moodle_all_courses

        # ── Compare users ─────────────────────────────────────────────────
        user_drifts = compare_users(telite_users, moodle_users)
        synced_users = len(telite_users) - sum(
            1 for d in user_drifts if d.drift_type in ("missing_in_moodle", "stale_ref")
        )
        report.users["synced"] = max(synced_users, 0)
        for item in user_drifts:
            if auto_fix and item.auto_fixable:
                _auto_fix_user_drift(item, org_id, telite_users)
                item.fixed = True
            report.add_item(item)

        # ── Compare courses ───────────────────────────────────────────────
        course_drifts = compare_courses(telite_courses, moodle_courses)
        synced_courses = len(telite_courses) - sum(
            1 for d in course_drifts if d.drift_type in ("missing_in_moodle", "stale_ref")
        )
        report.courses["synced"] = max(synced_courses, 0)
        for item in course_drifts:
            if auto_fix and item.auto_fixable:
                _auto_fix_course_drift(item, org_id, telite_courses)
                item.fixed = True
            report.add_item(item)

        # ── Compare enrollments per synced course ─────────────────────────
        synced_enrollment_count = 0
        for tc in telite_courses:
            moodle_course_id = tc.get("moodle_course_id")
            if not moodle_course_id:
                continue

            moodle_course_id = int(moodle_course_id)
            moodle_enrolled = moodle_get_enrolled_users(moodle_course_id)
            moodle_enrolled_ids = {int(u["id"]) for u in moodle_enrolled}

            # Get Telite approved enrollments for this course
            with get_conn() as conn:
                telite_enrollments = conn.execute(
                    """
                    SELECT er.id, er.email, u.id AS user_id, u.moodle_id
                    FROM enrollment_requests er
                    JOIN users u ON u.email = er.email AND u.org_id = er.org_id
                    WHERE er.org_id = ? AND er.status = 'approved'
                      AND er.category_slug = ?
                    """,
                    (org_id, tc.get("category_slug", "")),
                ).fetchall()
                telite_enrollments = [
                    dict(r) if not isinstance(r, dict) else r
                    for r in telite_enrollments
                ]

            enrollment_drifts = compare_enrollments(
                telite_enrollments,
                moodle_enrolled_ids,
                moodle_course_id,
                tc.get("name", ""),
            )

            matched = len(telite_enrollments) - sum(
                1 for d in enrollment_drifts if d.drift_type == "missing_enrollment"
            )
            synced_enrollment_count += max(matched, 0)

            for item in enrollment_drifts:
                if auto_fix and item.auto_fixable:
                    _auto_fix_enrollment_drift(item, org_id, tc, telite_enrollments)
                    item.fixed = True
                report.add_item(item)

        report.enrollments["synced"] = synced_enrollment_count

        # ── Compare categories ────────────────────────────────────────────
        category_drifts = compare_categories(telite_categories, moodle_categories)
        synced_cats = len(telite_categories) - sum(
            1 for d in category_drifts if d.drift_type in ("missing_in_moodle", "stale_ref")
        )
        report.categories["synced"] = max(synced_cats, 0)
        for item in category_drifts:
            if auto_fix and item.auto_fixable:
                _auto_fix_category_drift(item, org_id, telite_categories)
                item.fixed = True
            report.add_item(item)

        # ── Store drift report in sync logs ───────────────────────────────
        report_dict = report.to_dict()
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO moodle_sync_logs
                    (org_id, event_type, status, message, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    org_id,
                    "drift.report",
                    "completed",
                    (
                        f"Drift report: {len(report.details)} issues found, "
                        f"{report.auto_fixes_applied} auto-fixed, "
                        f"{report.issues_requiring_review} need review"
                    ),
                    json.dumps(report_dict),
                    now_local(),
                ),
            )
            conn.commit()

        logger.info(
            "Drift report org_id=%d: %d issues, %d auto-fixed, %d review",
            org_id,
            len(report.details),
            report.auto_fixes_applied,
            report.issues_requiring_review,
        )
        return report_dict

    except Exception as exc:
        logger.error("Drift report failed for org_id=%d: %s", org_id, exc)
        raise self.retry(exc=exc, countdown=120)


# ── Auto-fix helpers ─────────────────────────────────────────────────────────


def _auto_fix_user_drift(
    item, org_id: int, telite_users: list[dict[str, Any]]
) -> None:
    """Re-dispatch user sync for fixable drift items."""
    from app.integrations.moodle_events import publish_user_created

    if item.drift_type == "missing_in_moodle" and item.telite_id:
        user = next((u for u in telite_users if str(u["id"]) == item.telite_id), None)
        if user:
            publish_user_created(
                user_id=user["id"],
                username=user["username"],
                email=user["email"],
                full_name=user.get("full_name", ""),
                org_id=org_id,
            )
    elif item.drift_type == "stale_ref" and item.telite_id:
        # Clear stale moodle_id so next reconciliation re-syncs
        from app.services.store import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET moodle_id = NULL WHERE id = ?",
                (item.telite_id,),
            )
            conn.commit()
        # Re-dispatch creation
        user = next((u for u in telite_users if str(u["id"]) == item.telite_id), None)
        if user:
            publish_user_created(
                user_id=user["id"],
                username=user["username"],
                email=user["email"],
                full_name=user.get("full_name", ""),
                org_id=org_id,
            )


def _auto_fix_course_drift(
    item, org_id: int, telite_courses: list[dict[str, Any]]
) -> None:
    """Re-dispatch course sync for fixable drift items."""
    from app.integrations.moodle_events import publish_course_created

    if item.drift_type == "missing_in_moodle" and item.telite_id:
        course = next(
            (c for c in telite_courses if str(c["id"]) == item.telite_id), None
        )
        if course:
            publish_course_created(
                course_id=course["id"],
                name=course["name"],
                category_slug=course.get("category_slug", ""),
                org_id=org_id,
            )
    elif item.drift_type == "stale_ref" and item.telite_id:
        from app.services.store import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE courses SET moodle_course_id = NULL WHERE id = ?",
                (item.telite_id,),
            )
            conn.commit()
        course = next(
            (c for c in telite_courses if str(c["id"]) == item.telite_id), None
        )
        if course:
            publish_course_created(
                course_id=course["id"],
                name=course["name"],
                category_slug=course.get("category_slug", ""),
                org_id=org_id,
            )


def _auto_fix_enrollment_drift(
    item, org_id: int, course: dict, telite_enrollments: list[dict]
) -> None:
    """Re-dispatch enrollment sync for fixable drift items."""
    from app.integrations.moodle_events import publish_enrollment_approved

    if item.drift_type == "missing_enrollment" and item.telite_id:
        enrollment = next(
            (e for e in telite_enrollments if str(e.get("id", "")) == item.telite_id),
            None,
        )
        if enrollment:
            publish_enrollment_approved(
                enrollment_id=enrollment["id"],
                user_id=enrollment.get("user_id", ""),
                course_id=str(course["id"]),
                org_id=org_id,
                moodle_user_id=enrollment.get("moodle_id"),
                moodle_course_id=course.get("moodle_course_id"),
            )


def _auto_fix_category_drift(
    item, org_id: int, telite_categories: list[dict[str, Any]]
) -> None:
    """Re-dispatch category sync for fixable drift items."""
    from app.integrations.moodle_events import publish_category_created

    if item.drift_type == "missing_in_moodle" and item.telite_id:
        category = next(
            (c for c in telite_categories if str(c["id"]) == item.telite_id), None
        )
        if category:
            publish_category_created(
                category_id=category["id"],
                name=category["name"],
                slug=category.get("slug", ""),
                org_id=org_id,
                description=category.get("description", ""),
            )
    elif item.drift_type == "stale_ref" and item.telite_id:
        from app.services.store import get_conn
        with get_conn() as conn:
            conn.execute(
                "UPDATE categories SET moodle_category_id = NULL WHERE id = ?",
                (item.telite_id,),
            )
            conn.commit()
        category = next(
            (c for c in telite_categories if str(c["id"]) == item.telite_id), None
        )
        if category:
            publish_category_created(
                category_id=category["id"],
                name=category["name"],
                slug=category.get("slug", ""),
                org_id=org_id,
                description=category.get("description", ""),
            )


def _get_category_subtree_ids(
    all_categories: list[dict], parent_id: int
) -> set[int]:
    """Get all category IDs in the subtree rooted at parent_id (inclusive)."""
    ids = {parent_id}
    changed = True
    while changed:
        changed = False
        for cat in all_categories:
            cat_id = int(cat.get("id", 0))
            cat_parent = int(cat.get("parent", 0))
            if cat_parent in ids and cat_id not in ids:
                ids.add(cat_id)
                changed = True
    return ids


# ── Dead letter retry (Bug #4 fix) ──────────────────────────────────────────


@celery_app.task(
    name="app.workers.reconciliation.retry_dead_letter_events",
    queue="reconcile",
)
def retry_dead_letter_events() -> dict[str, Any]:
    """
    Hourly job: retry events stuck in dead_letter status.

    Previously only counted dead letters — now actually re-dispatches them
    via the event publisher and updates their status.
    """
    from app.services.store import get_conn, now_local
    from app.integrations.moodle_events import publish_moodle_event

    logger.info("Checking for dead-letter sync events to retry")

    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, org_id, event_type, metadata_json
                FROM moodle_sync_logs
                WHERE status = 'dead_letter'
                  AND created_at > datetime('now', '-7 days')
                ORDER BY created_at DESC
                LIMIT 20
                """,
            ).fetchall()

        count = len(rows)
        if count == 0:
            logger.info("No dead-letter events found")
            return {"status": "ok", "dead_letter_count": 0}

        retried = 0
        failed = 0

        for row in rows:
            r = dict(row) if not isinstance(row, dict) else row
            event_type = r.get("event_type", "")
            org_id = r.get("org_id", 0)
            log_id = r.get("id")
            metadata_raw = r.get("metadata_json")

            # Skip non-retryable event types
            if event_type in ("reconciliation", "drift.report"):
                continue

            # Parse metadata to reconstruct the record
            metadata: dict[str, Any] = {}
            if metadata_raw:
                try:
                    metadata = json.loads(metadata_raw)
                except (json.JSONDecodeError, TypeError):
                    pass

            if not metadata:
                logger.warning(
                    "Dead-letter id=%s has no metadata — cannot retry", log_id
                )
                failed += 1
                continue

            # Re-dispatch via the compatibility shim
            task_id = publish_moodle_event(metadata, event_type, org_id=org_id)

            if task_id:
                # Mark original dead letter as retried
                with get_conn() as conn:
                    conn.execute(
                        """
                        UPDATE moodle_sync_logs
                        SET status = 'retried', message = message || ' [retried at ' || ? || ']'
                        WHERE id = ?
                        """,
                        (now_local(), log_id),
                    )
                    conn.commit()
                retried += 1
                logger.info(
                    "Retried dead-letter id=%s event_type=%s new_task=%s",
                    log_id, event_type, task_id,
                )
            else:
                failed += 1
                logger.warning(
                    "Failed to retry dead-letter id=%s event_type=%s",
                    log_id, event_type,
                )

        logger.info(
            "Dead-letter retry complete: %d retried, %d failed out of %d",
            retried, failed, count,
        )
        return {
            "status": "retried",
            "total": count,
            "retried": retried,
            "failed": failed,
        }

    except Exception as exc:
        logger.error("Dead-letter retry failed: %s", exc)
        return {"status": "error", "error": str(exc)}
