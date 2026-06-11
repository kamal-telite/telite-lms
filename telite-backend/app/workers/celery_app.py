"""
Celery application configuration for Telite LMS.

Queues:
  notifications — Email and in-app notifications
  reconcile     — Nightly jobs (e.g. data consistency checks)
"""

from __future__ import annotations

import os

from celery import Celery
from celery.utils.log import get_task_logger
from kombu import Exchange, Queue

logger = get_task_logger("telite.workers")

# ── Redis broker / backend ────────────────────────────────────────────────────

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB_CELERY = os.getenv("REDIS_DB_CELERY", "1")  # separate DB from rate limiter

_auth = f":{REDIS_PASSWORD}@" if REDIS_PASSWORD else ""
BROKER_URL = f"redis://{_auth}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CELERY}"
RESULT_BACKEND = BROKER_URL


# ── Celery app ────────────────────────────────────────────────────────────────

celery_app = Celery(
    "telite",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.workers.reconciliation",
        "app.workers.notification_tasks",
        "app.workers.reminder_tasks",
    ],
)

# ── Queue definitions ─────────────────────────────────────────────────────────

default_exchange = Exchange("default", type="direct")
reconcile_exchange = Exchange("reconcile", type="direct")
notifications_exchange = Exchange("notifications", type="direct")
reminders_exchange = Exchange("reminders", type="direct")

celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("reconcile", reconcile_exchange, routing_key="reconcile"),
    Queue("notifications", notifications_exchange, routing_key="notifications"),
    Queue("reminders", reminders_exchange, routing_key="reminders"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.task_routes = {
    "app.workers.reconciliation.*": {"queue": "reconcile"},
    "app.workers.notification_tasks.*": {"queue": "notifications"},
    "app.workers.reminder_tasks.*": {"queue": "reminders"},
}

# ── Retry / reliability settings ──────────────────────────────────────────────

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Reliability
    task_acks_late=True,           # ack only after task completes
    task_reject_on_worker_lost=True,  # re-queue if worker dies mid-task
    worker_prefetch_multiplier=1,  # one task at a time per worker
    # Result expiry
    result_expires=3600,           # 1 hour
    # Retry defaults (overridden per task)
    task_max_retries=5,
    # Visibility timeout — must be > longest expected task duration
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour
        "max_retries": 3,
    },
)

# ── Beat schedule (periodic tasks) ───────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # Nightly reconciliation
    "reconcile-nightly": {
        "task": "app.workers.reconciliation.reconcile_all_orgs",
        "schedule": 86400,  # every 24 hours
        "options": {"queue": "reconcile"},
    },
    # Hourly: retry dead-letter events
    "retry-dead-letter-events": {
        "task": "app.workers.reconciliation.retry_dead_letter_events",
        "schedule": 3600,  # every hour
        "options": {"queue": "reconcile"},
    },
    # Every 5 minutes: flush pending email notifications
    "dispatch-pending-notifications": {
        "task": "app.workers.notification_tasks.dispatch_pending_notifications",
        "schedule": 300,  # every 5 minutes
        "options": {"queue": "notifications"},
    },
    # Every 12 hours: enrollment reminders
    "enrollment-reminders": {
        "task": "app.workers.reminder_tasks.enrollment_reminders",
        "schedule": 43200,  # every 12 hours
        "options": {"queue": "reminders"},
    },
    # Daily: course publication notifications
    "publication-reminders": {
        "task": "app.workers.reminder_tasks.publication_reminders",
        "schedule": 86400,  # every 24 hours
        "options": {"queue": "reminders"},
    },
    # Daily: review reminders
    "review-reminders": {
        "task": "app.workers.reminder_tasks.review_reminders",
        "schedule": 86400,  # every 24 hours
        "options": {"queue": "reminders"},
    },
}
