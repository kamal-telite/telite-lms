"""
Moodle sync observability API — Phase 5.

Provides platform and org admins visibility into the async Moodle sync queue:
  - Sync status per org
  - Recent sync log entries
  - Dead-letter event counts
  - Manual retry trigger
  - Celery worker health
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import TokenData, get_current_user, require_platform_admin, resolve_org_scope

logger = logging.getLogger("telite.moodle.sync_api")

moodle_sync_router = APIRouter(prefix="/api/moodle", tags=["Moodle Sync"])


# ── Sync status ───────────────────────────────────────────────────────────────

@moodle_sync_router.get("/sync/status")
def get_sync_status(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get Moodle sync status for an organisation.
    Platform admins can query any org; others are scoped to their own.
    """
    from app.services.store import get_conn

    scoped_org_id = resolve_org_scope(current_user, org_id)

    with get_conn() as conn:
        # Recent sync logs
        rows = conn.execute(
            """
            SELECT event_type, status, message, duration_ms, created_at
            FROM moodle_sync_logs
            WHERE org_id = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (scoped_org_id,),
        ).fetchall()

        logs = [dict(r) if not isinstance(r, dict) else r for r in rows]

        # Count by status
        counts = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM moodle_sync_logs
            WHERE org_id = ?
              AND created_at > datetime('now', '-24 hours')
            GROUP BY status
            """,
            (scoped_org_id,),
        ).fetchall()

        status_counts = {
            (r["status"] if isinstance(r, dict) else r[0]):
            (r["count"] if isinstance(r, dict) else r[1])
            for r in counts
        }

        # Unsynced counts
        unsynced_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE org_id = ? AND moodle_id IS NULL AND role = 'learner' AND is_active = 1",
            (scoped_org_id,),
        ).fetchone()
        unsynced_courses = conn.execute(
            "SELECT COUNT(*) FROM courses WHERE org_id = ? AND moodle_course_id IS NULL AND status = 'active'",
            (scoped_org_id,),
        ).fetchone()

        def _count(row: Any) -> int:
            if row is None:
                return 0
            return row[0] if not isinstance(row, dict) else list(row.values())[0]

    return {
        "org_id": scoped_org_id,
        "last_24h": status_counts,
        "unsynced": {
            "users": _count(unsynced_users),
            "courses": _count(unsynced_courses),
        },
        "recent_logs": logs[:10],
        "dead_letter_count": status_counts.get("dead_letter", 0),
    }


@moodle_sync_router.get("/sync/logs")
def get_sync_logs(
    org_id: int | None = Query(default=None, alias="orgId"),
    event_type: str | None = Query(default=None),
    sync_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    current_user: TokenData = Depends(get_current_user),
) -> dict[str, Any]:
    """Get paginated Moodle sync logs for an organisation."""
    from app.services.store import get_conn

    scoped_org_id = resolve_org_scope(current_user, org_id)

    clauses = ["org_id = ?"]
    params: list[Any] = [scoped_org_id]

    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if sync_status:
        clauses.append("status = ?")
        params.append(sync_status)

    where = " AND ".join(clauses)
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, event_type, status, message, duration_ms,
                   metadata_json, created_at
            FROM moodle_sync_logs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

    return {
        "org_id": scoped_org_id,
        "logs": [dict(r) if not isinstance(r, dict) else r for r in rows],
        "count": len(rows),
    }


# ── Manual reconciliation trigger ─────────────────────────────────────────────

@moodle_sync_router.post("/sync/{org_id}")
def trigger_sync(
    org_id: int,
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """
    Platform admin: manually trigger Moodle reconciliation for an org.
    Dispatches the reconcile_org Celery task immediately.
    """
    try:
        from app.workers.reconciliation import reconcile_org
        task = reconcile_org.apply_async(
            kwargs={"org_id": org_id},
            queue="reconcile",
        )
        logger.info(
            "Manual sync triggered for org_id=%d by platform_admin=%s task_id=%s",
            org_id,
            current_user.id,
            task.id,
        )
        return {
            "status": "dispatched",
            "org_id": org_id,
            "task_id": task.id,
            "message": f"Reconciliation task dispatched for org {org_id}",
        }
    except Exception as exc:
        logger.error("Failed to dispatch reconciliation for org %d: %s", org_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not dispatch reconciliation task: {exc}",
        )


@moodle_sync_router.post("/sync-all")
def trigger_sync_all(
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """Platform admin: trigger reconciliation for ALL active organisations."""
    try:
        from app.workers.reconciliation import reconcile_all_orgs
        task = reconcile_all_orgs.apply_async(queue="reconcile")
        logger.info(
            "Full sync triggered by platform_admin=%s task_id=%s",
            current_user.id,
            task.id,
        )
        return {
            "status": "dispatched",
            "task_id": task.id,
            "message": "Full reconciliation dispatched for all active organisations",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not dispatch full reconciliation: {exc}",
        )


# ── Celery worker health ───────────────────────────────────────────────────────

@moodle_sync_router.get("/workers/health")
def worker_health(
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """
    Platform admin: check Celery worker health.
    Returns active workers, queue depths, and broker connectivity.
    """
    try:
        from app.workers.celery_app import celery_app

        # Ping workers (1 second timeout)
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        stats = inspect.stats() or {}

        worker_count = len(active)
        total_active_tasks = sum(len(tasks) for tasks in active.values())

        # Queue depths via Redis
        queue_depths: dict[str, int] = {}
        try:
            from app.core.rate_limiter import _get_redis_client
            redis_client = _get_redis_client()
            if redis_client:
                for queue_name in ("moodle_sync", "reconcile", "default"):
                    depth = redis_client.llen(queue_name)
                    queue_depths[queue_name] = depth
        except Exception:
            pass

        return {
            "status": "ok" if worker_count > 0 else "no_workers",
            "worker_count": worker_count,
            "active_tasks": total_active_tasks,
            "queue_depths": queue_depths,
            "workers": list(active.keys()),
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "worker_count": 0,
            "message": "Could not reach Celery workers — is the worker process running?",
        }


# ── Dead-letter management ────────────────────────────────────────────────────

@moodle_sync_router.get("/sync/dead-letters")
def list_dead_letters(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """List dead-letter sync events requiring manual review."""
    from app.services.store import get_conn

    params: list[Any] = ["dead_letter"]
    where = "status = ?"
    if org_id:
        where += " AND org_id = ?"
        params.append(org_id)

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, org_id, event_type, message, metadata_json, created_at
            FROM moodle_sync_logs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()

    return {
        "dead_letters": [dict(r) if not isinstance(r, dict) else r for r in rows],
        "count": len(rows),
    }


# ── Drift comparison API (Phase 5 completion) ────────────────────────────────


@moodle_sync_router.post("/drift/{org_id}", status_code=202)
def trigger_drift_report(
    org_id: int,
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """
    Platform admin: trigger a full drift comparison for an org.

    Dispatches build_drift_report Celery task which queries live Moodle
    read APIs and compares against Telite DB state.

    Returns 202 Accepted with the task ID — report is built asynchronously.
    """
    try:
        from app.workers.reconciliation import build_drift_report
        task = build_drift_report.apply_async(
            kwargs={"org_id": org_id, "auto_fix": False},
            queue="reconcile",
        )
        logger.info(
            "Drift report triggered for org_id=%d by admin=%s task_id=%s",
            org_id,
            current_user.id,
            task.id,
        )
        return {
            "status": "accepted",
            "org_id": org_id,
            "task_id": task.id,
            "message": f"Drift comparison queued for org {org_id}. Check GET /api/moodle/drift/{org_id} for results.",
        }
    except Exception as exc:
        logger.error("Failed to trigger drift report for org %d: %s", org_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not dispatch drift comparison task: {exc}",
        )


@moodle_sync_router.get("/drift/{org_id}")
def get_drift_report(
    org_id: int,
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """
    Platform admin: get the latest drift report for an org.

    Reads the most recent drift.report entry from moodle_sync_logs.
    """
    import json as _json
    from app.services.store import get_conn

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, org_id, event_type, status, message,
                   metadata_json, created_at
            FROM moodle_sync_logs
            WHERE org_id = ? AND event_type = 'drift.report'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (org_id,),
        ).fetchone()

    if not row:
        return {
            "org_id": org_id,
            "status": "no_report",
            "message": "No drift report available. Trigger one with POST /api/moodle/drift/{org_id}",
        }

    r = dict(row) if not isinstance(row, dict) else row
    report_data: dict[str, Any] = {}
    if r.get("metadata_json"):
        try:
            report_data = _json.loads(r["metadata_json"])
        except (_json.JSONDecodeError, TypeError):
            pass

    return {
        "org_id": org_id,
        "log_id": r.get("id"),
        "status": r.get("status", "unknown"),
        "message": r.get("message", ""),
        "created_at": r.get("created_at"),
        "report": report_data,
    }


@moodle_sync_router.post("/drift/{org_id}/fix", status_code=202)
def trigger_drift_fix(
    org_id: int,
    current_user: TokenData = Depends(require_platform_admin),
) -> dict[str, Any]:
    """
    Platform admin: trigger drift comparison with auto-fix for resolvable items.

    Same as trigger_drift_report but with auto_fix=True.
    Auto-fixable items (missing syncs, stale refs) are automatically re-dispatched.
    """
    try:
        from app.workers.reconciliation import build_drift_report
        task = build_drift_report.apply_async(
            kwargs={"org_id": org_id, "auto_fix": True},
            queue="reconcile",
        )
        logger.info(
            "Drift fix triggered for org_id=%d by admin=%s task_id=%s",
            org_id,
            current_user.id,
            task.id,
        )
        return {
            "status": "accepted",
            "org_id": org_id,
            "task_id": task.id,
            "auto_fix": True,
            "message": f"Drift comparison with auto-fix queued for org {org_id}.",
        }
    except Exception as exc:
        logger.error("Failed to trigger drift fix for org %d: %s", org_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not dispatch drift fix task: {exc}",
        )

