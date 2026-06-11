"""
Celery tasks for scheduled reminders — Telite LMS.

Tasks:
  enrollment_reminders    — notify admins of pending enrollment requests
  publication_reminders   — notify learners of new course publications
  review_reminders        — notify instructors/reviewers of pending assignments
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.workers.celery_app import celery_app

logger = logging.getLogger("telite.workers.reminders")


@celery_app.task(
    name="app.workers.reminder_tasks.enrollment_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def enrollment_reminders(self) -> dict:
    """
    Scan for pending enrollment requests older than 24 hours and notify admins.
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from app.workers.notification_tasks import send_email_notification
        from sqlalchemy import text

        orgs_processed = 0
        reminders_sent = 0

        with get_platform_session() as platform_session:
            active_orgs = platform_session.execute(
                text("SELECT id FROM organizations WHERE status = 'active'")
            ).scalars().all()

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        for org_id in active_orgs:
            try:
                with get_tenant_session(org_id) as tenant_session:
                    # Count pending requests
                    pending_count = tenant_session.execute(
                        text(
                            "SELECT COUNT(*) FROM enrollment_requests "
                            "WHERE status = 'pending' AND created_at <= :yesterday"
                        ),
                        {"yesterday": yesterday}
                    ).scalar_one()

                    if pending_count > 0:
                        # Find platform admins for this org to notify
                        admins = tenant_session.execute(
                            text(
                                "SELECT email, full_name FROM users "
                                "WHERE org_id = :org_id AND role IN ('admin', 'superadmin') "
                                "AND is_active = true AND email IS NOT NULL"
                            ),
                            {"org_id": org_id}
                        ).fetchall()

                        for admin in admins:
                            send_email_notification.delay(
                                to_email=admin.email,
                                name=admin.full_name or "Admin",
                                title="Pending Enrollment Requests",
                                body=f"You have {pending_count} pending enrollment requests waiting for approval.",
                                org_id=org_id,
                                notif_type="reminder"
                            )
                            reminders_sent += 1
                orgs_processed += 1
            except Exception as org_exc:
                logger.error("Failed processing enrollment reminders for org %d: %s", org_id, org_exc)
                continue

        return {"orgs_processed": orgs_processed, "reminders_sent": reminders_sent}
    except Exception as exc:
        logger.error("Enrollment reminders task failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.reminder_tasks.publication_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def publication_reminders(self) -> dict:
    """
    Notify active learners about newly published courses in the last 24 hours.
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from app.workers.notification_tasks import send_email_notification
        from sqlalchemy import text

        orgs_processed = 0
        reminders_sent = 0

        with get_platform_session() as platform_session:
            active_orgs = platform_session.execute(
                text("SELECT id FROM organizations WHERE status = 'active'")
            ).scalars().all()

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        for org_id in active_orgs:
            try:
                with get_tenant_session(org_id) as tenant_session:
                    # Find newly published courses
                    new_courses = tenant_session.execute(
                        text(
                            "SELECT title FROM courses "
                            "WHERE is_published = true AND created_at >= :yesterday "
                            "AND org_id = :org_id"
                        ),
                        {"yesterday": yesterday, "org_id": org_id}
                    ).scalars().all()

                    if new_courses:
                        course_list = ", ".join(new_courses)
                        # Notify all active learners
                        learners = tenant_session.execute(
                            text(
                                "SELECT email, full_name FROM users "
                                "WHERE org_id = :org_id AND role IN ('learner', 'student') "
                                "AND is_active = true AND email IS NOT NULL"
                            ),
                            {"org_id": org_id}
                        ).fetchall()

                        for learner in learners:
                            send_email_notification.delay(
                                to_email=learner.email,
                                name=learner.full_name or "Learner",
                                title="New Courses Published!",
                                body=f"New courses are now available: {course_list}",
                                org_id=org_id,
                                notif_type="announcement"
                            )
                            reminders_sent += 1
                orgs_processed += 1
            except Exception as org_exc:
                logger.error("Failed processing publication reminders for org %d: %s", org_id, org_exc)
                continue

        return {"orgs_processed": orgs_processed, "reminders_sent": reminders_sent}
    except Exception as exc:
        logger.error("Publication reminders task failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.reminder_tasks.review_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def review_reminders(self) -> dict:
    """
    Notify instructors/reviewers about pending assignment submissions.
    """
    try:
        from app.db.engine import get_platform_session, get_tenant_session
        from app.workers.notification_tasks import send_email_notification
        from sqlalchemy import text

        orgs_processed = 0
        reminders_sent = 0

        with get_platform_session() as platform_session:
            active_orgs = platform_session.execute(
                text("SELECT id FROM organizations WHERE status = 'active'")
            ).scalars().all()

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)

        for org_id in active_orgs:
            try:
                with get_tenant_session(org_id) as tenant_session:
                    # In a real implementation, we'd query pending assignment_submissions.
                    # As a placeholder, we just log that we would process them here.
                    # pending_reviews = tenant_session.execute(...)
                    pass
                orgs_processed += 1
            except Exception as org_exc:
                logger.error("Failed processing review reminders for org %d: %s", org_id, org_exc)
                continue

        return {"orgs_processed": orgs_processed, "reminders_sent": reminders_sent}
    except Exception as exc:
        logger.error("Review reminders task failed: %s", exc)
        raise self.retry(exc=exc)
