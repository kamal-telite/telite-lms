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
        from app.db.engine import get_platform_session
        from app.services.email import _dispatch_notification_email
        from sqlalchemy import text
        import json

        dispatched = 0
        failed = 0

        with get_platform_session() as session:
            # Fetch up to 50 pending email notifications
            rows = session.execute(
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
                        session.execute(
                            text(
                                "UPDATE notifications SET metadata_json = :meta WHERE id = :id"
                            ),
                            {"meta": json.dumps(meta), "id": row.id},
                        )
                        dispatched += 1
                        logger.info("Notification %d dispatched to %s", row.id, row.email)
                    else:
                        failed += 1

                except Exception as row_exc:
                    logger.error("Failed to dispatch notification %d: %s", row.id, row_exc)
                    failed += 1

        summary = {
            "status": "completed",
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
    notif_type: str = "info",
) -> bool:
    """
    Send a single email notification immediately.

    Called directly from route handlers when real-time delivery is needed
    (e.g. enrollment approval, task assignment).
    """
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
        return True
    except Exception as exc:
        logger.error("send_email_notification failed for %s: %s", to_email, exc)
        raise self.retry(exc=exc)
