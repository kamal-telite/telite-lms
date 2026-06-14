"""Celery tasks for analytics stream rollups."""

from __future__ import annotations

import logging
import os

from app.workers.analytics_worker import run_analytics_rollup
from app.workers.celery_app import celery_app

logger = logging.getLogger("telite.analytics_tasks")


@celery_app.task(name="app.workers.analytics_tasks.process_analytics_rollups")
def process_analytics_rollups() -> dict[str, int]:
    if os.getenv("REDIS_ENABLED", "true").lower() not in ("true", "1", "yes"):
        logger.info("Redis disabled — skipping analytics rollup")
        return {"processed_orgs": 0}

    try:
        import redis
        from sqlalchemy import text

        from app.db.engine import get_db_session

        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=False,
        )
        redis_client.ping()

        with get_db_session() as session:
            rows = session.execute(
                text("SELECT id FROM organizations WHERE status = 'active'")
            ).fetchall()
        org_ids = [int(row[0]) for row in rows]

        run_analytics_rollup(redis_client, org_ids)
        return {"processed_orgs": len(org_ids)}
    except Exception:
        logger.exception("Analytics rollup failed")
        raise
