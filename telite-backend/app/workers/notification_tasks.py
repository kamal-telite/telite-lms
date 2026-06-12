"""
Celery tasks for async notification dispatch — Telite LMS.

Tasks:
  dispatch_pending_notifications — flush undelivered Notification rows to email
  send_email_notification        — send a single email notification immediately
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger("telite.workers.notifications")


@celery_app.task(
    name="app.workers.notification_tasks.dispatch_pending_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_pending_notifications(self) -> dict:
    """
    Scan for Notification rows that have `delivery_channel='email'` and
    `delivered_at IS NULL`, then send them via SMTP.

    Called periodically by Celery Beat (every 5 minutes).
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from app.services.email import _dispatch_notification_email
        from app.repositories.audit_repo import AuditRepository
        from sqlalchemy import text
        import json

        dispatched = 0
        failed = 0
        orgs_processed = 0

        with get_platform_session() as platform_session:
            active_orgs = platform_session.execute(
                text("SELECT id FROM organizations WHERE status = 'active' ORDER BY id")
            ).scalars().all()

        for org_id in active_orgs:
            try:
                with get_tenant_session(org_id) as tenant_session:
                    # Fetch up to 50 pending email notifications per org
                    rows = tenant_session.execute(
                        text(
                            """
                            SELECT n.id, n.user_id, n.org_id, n.title, n.body,
                                   n.type, n.metadata_json,
                                   u.email, u.full_name
                            FROM notifications n
                            JOIN users u ON u.id = n.user_id
                            WHERE n.is_read = false
                              AND (n.metadata_json IS NULL
                                   OR n.metadata_json NOT LIKE '%"delivered_at"%')
                              AND u.email IS NOT NULL
                            ORDER BY n.created_at ASC
                            LIMIT 50
                            """
                        )
                    ).fetchall()

                    for row in rows:
                        try:
                            meta = json.loads(row.metadata_json or "{}")

                            # Only dispatch if this notification requested email delivery
                            if meta.get("delivery_channel") != "email":
                                continue

                            success = _dispatch_notification_email(
                                to_email=row.email,
                                name=row.full_name or row.user_id,
                                title=row.title,
                                body=row.body,
                                notif_type=row.type,
                            )

                            if success:
                                meta["delivered_at"] = datetime.now(timezone.utc).isoformat()
                                meta["delivery_method"] = "smtp"
                                tenant_session.execute(
                                    text(
                                        "UPDATE notifications SET metadata_json = :meta WHERE id = :id"
                                    ),
                                    {"meta": json.dumps(meta), "id": row.id},
                                )
                                dispatched += 1
                                logger.info("Notification %d dispatched to %s", row.id, row.email)
                                AuditRepository(tenant_session).write(
                                    actor_user_id=None,
                                    actor_name="system",
                                    action="notification.sent",
                                    target_type="notification",
                                    target_id=str(row.id),
                                    org_id=org_id,
                                    message=f"Sent {row.type} notification to {row.email}",
                                    result="success",
                                )
                            else:
                                failed += 1
                                AuditRepository(tenant_session).write(
                                    actor_user_id=None,
                                    actor_name="system",
                                    action="notification.failed",
                                    target_type="notification",
                                    target_id=str(row.id),
                                    org_id=org_id,
                                    message=f"Failed to send {row.type} notification to {row.email}",
                                    result="failed",
                                )

                        except Exception as row_exc:
                            logger.error("Failed to dispatch notification %d: %s", row.id, row_exc)
                            failed += 1
                            AuditRepository(tenant_session).write(
                                actor_user_id=None,
                                actor_name="system",
                                action="notification.error",
                                target_type="notification",
                                target_id=str(row.id),
                                org_id=org_id,
                                message=f"Error dispatching notification: {row_exc}",
                                result="failed",
                            )

                    tenant_session.commit()
                orgs_processed += 1
            except Exception as org_exc:
                logger.error("Failed processing org %d notifications: %s", org_id, org_exc)
                continue

        summary = {
            "status": "completed",
            "orgs_processed": orgs_processed,
            "dispatched": dispatched,
            "failed": failed,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Notification dispatch complete: %s", summary)
        return summary

    except Exception as exc:
        logger.error("Notification dispatch task failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.notification_tasks.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_email_notification(
    self,
    *,
    to_email: str,
    name: str,
    title: str,
    body: str,
    org_id: int = 0,
    notif_type: str = "info",
) -> bool:
    """
    Send a single email notification immediately.

    Called directly from route handlers when real-time delivery is needed
    (e.g. enrollment approval, task assignment).
    """
    from app.db.engine import get_platform_session, get_tenant_session
    from app.repositories.audit_repo import AuditRepository

    def _log_audit(action: str, result: str, msg: str, metadata: dict = None):
        if org_id > 0:
            with get_tenant_session(org_id) as session:
                AuditRepository(session).write(
                    actor_user_id=None,
                    actor_name="system",
                    action=action,
                    target_type="email",
                    target_id=to_email,
                    org_id=org_id,
                    message=msg,
                    result=result,
                    metadata=metadata,
                )
                session.commit()
        else:
            with get_platform_session() as session:
                AuditRepository(session).write(
                    actor_user_id=None,
                    actor_name="system",
                    action=action,
                    target_type="email",
                    target_id=to_email,
                    org_id=0,
                    message=msg,
                    result=result,
                    metadata=metadata,
                )
                session.commit()

    try:
        from app.services.email import _dispatch_notification_email
        success = _dispatch_notification_email(
            to_email=to_email,
            name=name,
            title=title,
            body=body,
            notif_type=notif_type,
        )
        if not success:
            raise RuntimeError(f"Email delivery returned False for {to_email}")
            
        _log_audit("notification.sent", "success", f"Sent {notif_type} to {to_email}")
        return True
    except Exception as exc:
        logger.error("send_email_notification failed for %s: %s", to_email, exc)
        retry_count = self.request.retries
        if retry_count >= self.max_retries:
            # Dead letter
            _log_audit(
                action="notification.dead_letter",
                result="failed",
                msg=f"Dead letter: failed to send to {to_email}",
                metadata={
                    "task_name": self.name,
                    "payload": {"to_email": to_email, "title": title},
                    "error": str(exc),
                    "retry_count": retry_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        else:
            _log_audit(
                action="notification.retry",
                result="failed",
                msg=f"Retrying notification to {to_email} ({retry_count + 1}/{self.max_retries})",
                metadata={"error": str(exc)}
            )
        raise self.retry(exc=exc)
