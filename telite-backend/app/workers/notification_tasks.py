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
    import json

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


@celery_app.task(name="notifications.dispatch_fanout", bind=True, max_retries=3)
def dispatch_fanout_task(
    self,
    event_name: str,
    org_id: int,
    context: dict,
    audience: dict
):
    """
    Dispatches a single domain event to a large audience using batched inserts.
    """
    import os
    from app.db.engine import get_tenant_session
    from app.services.notification_service import NotificationService
    from app.services.preference_resolver import PreferenceResolver
    from app.services.notification_category_mapper import event_to_category
    from sqlalchemy import select
    from app.models.user import User

    logger.info("Starting fanout for event %s to org %d", event_name, org_id)
    
    with get_tenant_session(org_id) as db:
        service = NotificationService(db)
        resolver = PreferenceResolver(db)
        payload = service._build_payload(event_name, context)
        
        if not payload:
            logger.warning("Fanout aborted: event %s produced no payload", event_name)
            return

        # Resolve audience
        audience_type = audience.get("type")
        recipient_ids = []
        
        if audience_type == "org_all":
            stmt = select(User.id).where(User.org_id == org_id, User.is_active == True)
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "course_enrolled":
            course_id = audience.get("course_id")
            from app.models.course_progress import CourseProgress
            stmt = select(CourseProgress.user_id).where(
                CourseProgress.course_id == course_id,
                CourseProgress.org_id == org_id,
                CourseProgress.status != "dropped"
            )
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "category_enrolled":
            category_slug = audience.get("category_slug")
            stmt = select(User.id).where(
                User.org_id == org_id,
                User.is_active == True,
                User.category_scope == category_slug
            )
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "all":
            stmt = select(User.id).where(User.org_id == org_id, User.is_active == True)
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "role":
            stmt = select(User.id).where(
                User.org_id == org_id,
                User.role == audience.get("value"),
                User.is_active == True
            )
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "category":
            stmt = select(User.id).where(
                User.org_id == org_id,
                User.category_scope == audience.get("value"),
                User.is_active == True
            )
            recipient_ids = db.execute(stmt).scalars().all()
        elif audience_type == "user":
            uid = audience.get("value")
            stmt = select(User.id).where(User.id == uid, User.org_id == org_id, User.is_active == True)
            recipient_ids = db.execute(stmt).scalars().all()
        else:
            logger.error("Unknown audience type: %s", audience_type)
            return

        logger.info("Resolved %d recipients for %s", len(recipient_ids), event_name)
        if not recipient_ids:
            return

        category_str = event_to_category(event_name)
        
        # Batch resolution to avoid N+1
        prefs_batch = resolver.resolve_for_users_batch(recipient_ids, org_id, category_str)

        count = 0
        batch_size = int(os.getenv("NOTIFICATION_BULK_BATCH_SIZE", "500"))
        notif_type = getattr(payload["type"], "value", payload["type"])
        
        for uid in recipient_ids:
            prefs = prefs_batch.get(uid, {"in_app": True, "email": True})
            
            if not prefs["in_app"] and not prefs["email"]:
                continue
                
            metadata = dict(payload.get("metadata", {}))
            if prefs["email"]:
                metadata["delivery_channel"] = "email"
            if not prefs["in_app"]:
                metadata["hidden_in_app"] = True
                
            service.repo.create_once(
                user_id=str(uid),
                org_id=org_id,
                title=payload["title"],
                message=payload["message"],
                notif_type=notif_type,
                idempotency_key=payload["idempotency_key"],
                metadata=metadata,
                source_type=payload["source_type"],
                source_id=payload["source_id"]
            )
            count += 1
            if count % batch_size == 0:
                db.flush()
                
        db.commit()
        logger.info("Fanout complete for %s. Inserted %d notifications.", event_name, count)
