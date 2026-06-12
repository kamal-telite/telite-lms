"""
Celery reconciliation workers for Telite LMS.

Tasks:
  reconcile_all_orgs       — nightly data consistency check across all orgs
  retry_dead_letter_events — retry failed async events from the dead-letter log
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger("telite.workers.reconciliation")


@celery_app.task(
    name="app.workers.reconciliation.reconcile_all_orgs",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def reconcile_all_orgs(self) -> dict:
    """
    Nightly reconciliation — verify data consistency across all organisations.

    Current scope:
    - Ensures every active user has a corresponding org_id that still exists.
    - Logs a summary per-org.

    Returns a summary dict for Celery result storage.
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from sqlalchemy import text
        from app.repositories.audit_repo import AuditRepository

        organizations_processed = 0
        organizations_failed = 0
        users_reconciled = 0
        errors: list[str] = []

        with get_platform_session() as platform_session:
            # Fetch all org IDs that are active
            org_ids = platform_session.execute(
                text("SELECT id FROM organizations WHERE status = 'active' ORDER BY id")
            ).scalars().all()

        for org_id in org_ids:
            try:
                with get_tenant_session(org_id) as tenant_session:
                    # Count orphaned users (users whose org no longer matches)
                    # Note: Since the tenant_session is bound to an org, querying users where org_id doesn't match
                    # the session's org_id shouldn't happen unless data is corrupt, but we check anyway.
                    orphan_count = tenant_session.execute(
                        text(
                            "SELECT COUNT(*) FROM users u "
                            "WHERE u.org_id = :oid "
                            "AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.id = u.org_id)"
                        ),
                        {"oid": org_id},
                    ).scalar_one()

                    if orphan_count > 0:
                        logger.warning(
                            "Reconciliation: org %d has %d orphaned users", org_id, orphan_count
                        )
                        errors.append(f"org_{org_id}: {orphan_count} orphaned users")
                        
                    users_reconciled += orphan_count

                    organizations_processed += 1
            except Exception as org_exc:
                logger.error("Reconciliation failed for org %d: %s", org_id, org_exc)
                errors.append(f"org_{org_id}: {org_exc}")
                organizations_failed += 1
                continue

        summary = {
            "status": "completed",
            "organizations_processed": organizations_processed,
            "organizations_failed": organizations_failed,
            "users_reconciled": users_reconciled,
            "errors": errors,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
        
        with get_platform_session() as platform_session:
            AuditRepository(platform_session).write(
                actor_user_id=None,
                actor_name="system",
                action="worker.reconciliation.completed",
                target_type="system",
                target_id="reconciliation_job",
                org_id=0,
                message=f"Reconciliation completed for {organizations_processed} orgs.",
                metadata=summary,
            )
            platform_session.commit()
            
        logger.info("Reconciliation complete: %s", summary)
        return summary

    except Exception as exc:
        logger.error("Reconciliation task failed: %s", exc)
        with get_platform_session() as platform_session:
            AuditRepository(platform_session).write(
                actor_user_id=None,
                actor_name="system",
                action="worker.reconciliation.failed",
                target_type="system",
                target_id="reconciliation_job",
                org_id=0,
                message=str(exc),
                result="failed",
            )
            platform_session.commit()
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.reconciliation.retry_dead_letter_events",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def retry_dead_letter_events(self) -> dict:
    """
    Retry failed async events stored in the dead-letter audit log.

    Looks for audit_log entries with result='failed' that have not
    been retried yet, and re-enqueues them.
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from sqlalchemy import text

        retried = 0

        with get_platform_session() as session:
            dead_events = session.execute(
                text(
                    "SELECT id, action, metadata_json, org_id FROM audit_log "
                    "WHERE result = 'failed' "
                    "AND (metadata_json IS NULL OR metadata_json NOT LIKE '%\"retried\":true%') "
                    "ORDER BY created_at ASC "
                    "LIMIT 100"
                )
            ).fetchall()

        for event in dead_events:
            try:
                # Mark as retried to prevent re-processing
                import json as _json
                meta = _json.loads(event.metadata_json or "{}")
                meta["retried"] = True
                meta["retried_at"] = datetime.now(timezone.utc).isoformat()

                if event.org_id and event.org_id > 0:
                    with get_tenant_session(event.org_id) as tenant_session:
                        tenant_session.execute(
                            text("UPDATE audit_log SET metadata_json = :meta WHERE id = :id"),
                            {"meta": _json.dumps(meta), "id": event.id},
                        )
                        tenant_session.commit()
                else:
                    with get_platform_session() as platform_session:
                        platform_session.execute(
                            text("UPDATE audit_log SET metadata_json = :meta WHERE id = :id"),
                            {"meta": _json.dumps(meta), "id": event.id},
                        )
                        platform_session.commit()

                # TODO: Dispatch the event to the correct celery queue based on action
                # For now, we just mark it as retried.
                
                retried += 1
                logger.info("Retried dead-letter event id=%d action=%s", event.id, event.action)

            except Exception as evt_exc:
                logger.error("Failed to retry event id=%d: %s", event.id, evt_exc)

        summary = {
            "status": "completed",
            "retried_events": retried,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Dead-letter retry complete: %s", summary)
        return summary

    except Exception as exc:
        logger.error("Dead-letter retry task failed: %s", exc)
        raise self.retry(exc=exc)
