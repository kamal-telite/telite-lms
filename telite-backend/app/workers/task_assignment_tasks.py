"""
Celery tasks for bulk TaskAssignment generation — Telite LMS.

Tasks:
  generate_bulk_assignments — Fan-out TaskAssignment rows for scope="all" tasks.
  backfill_global_tasks     — One-shot backfill for existing global tasks.
  generate_enrollment_assignments — Assign pending global tasks to a newly enrolled learner.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger("telite.workers.task_assignments")

# Configurable batch size for bulk inserts (default: 500 rows per batch)
BATCH_SIZE = int(os.getenv("TASK_ASSIGNMENT_BATCH_SIZE", "500"))


@celery_app.task(
    name="app.workers.task_assignment_tasks.generate_bulk_assignments",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
)
def generate_bulk_assignments(self, task_id: str, org_id: int) -> dict:
    """
    Generate TaskAssignment rows for every active learner in the organisation.

    Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
    Updates the task's assignment_generation_status on success/failure.
    """
    try:
        from sqlalchemy import text
        from app.db.engine import get_db_session
        from app.models.task import Task
        from app.models.user import User

        with get_db_session() as session:
            # Mark generation as started
            task = session.get(Task, task_id)
            if not task:
                logger.error("Task %s not found, skipping bulk generation.", task_id)
                return {"status": "error", "reason": "task_not_found"}

            task.generation_started_at = datetime.now(timezone.utc)
            task.assignment_generation_status = "in_progress"
            task.generation_error = None
            session.commit()

        # Fetch all active learner IDs in the org
        with get_db_session() as session:
            from sqlalchemy import select, func
            learner_ids = session.execute(
                select(User.id).where(
                    User.org_id == org_id,
                    User.role == "learner",
                    User.is_active.is_(True),
                )
            ).scalars().all()

        if not learner_ids:
            with get_db_session() as session:
                task = session.get(Task, task_id)
                if task:
                    task.assignment_generation_status = "completed"
                    task.generation_completed_at = datetime.now(timezone.utc)
                    session.commit()
            logger.info("No active learners for org %d, task %s generation complete.", org_id, task_id)
            return {"status": "completed", "created": 0, "total_learners": 0}

        # Batched bulk insert with ON CONFLICT DO NOTHING
        total_created = 0
        now = datetime.now(timezone.utc)

        for i in range(0, len(learner_ids), BATCH_SIZE):
            batch = learner_ids[i:i + BATCH_SIZE]
            with get_db_session() as session:
                from app.db.engine import is_postgres_dsn

                if is_postgres_dsn():
                    # PostgreSQL: use parameterized INSERT ... ON CONFLICT DO NOTHING
                    from sqlalchemy.dialects.postgresql import insert
                    from app.models.task_workflow import TaskAssignment
                    
                    values = [
                        {
                            "task_id": task_id,
                            "learner_id": lid,
                            "status": "assigned",
                            "assigned_at": now,
                            "org_id": org_id,
                        }
                        for lid in batch
                    ]
                    stmt = insert(TaskAssignment).values(values)
                    stmt = stmt.on_conflict_do_nothing(index_elements=['task_id', 'learner_id'])
                    result = session.execute(stmt)
                    total_created += result.rowcount
                else:
                    # SQLite fallback: INSERT OR IGNORE via nested transactions (savepoints)
                    from app.models.task_workflow import TaskAssignment
                    for lid in batch:
                        try:
                            with session.begin_nested():
                                assignment = TaskAssignment(
                                    task_id=task_id,
                                    learner_id=lid,
                                    status="assigned",
                                    assigned_at=now,
                                    org_id=org_id,
                                )
                                session.add(assignment)
                            total_created += 1
                        except Exception:
                            # Nested transaction is automatically rolled back on exception.
                            # The outer session is unaffected, preserving earlier inserts in the batch.
                            continue

                session.commit()

        # Mark generation as completed
        with get_db_session() as session:
            task = session.get(Task, task_id)
            if task:
                task.assignment_generation_status = "completed"
                task.generation_completed_at = datetime.now(timezone.utc)
                task.generation_error = None
                session.commit()

        logger.info(
            "Bulk assignment generation complete for task %s: %d/%d learners.",
            task_id, total_created, len(learner_ids),
        )
        return {"status": "completed", "created": total_created, "total_learners": len(learner_ids)}

    except Exception as exc:
        logger.exception("Bulk assignment generation failed for task %s", task_id)

        # Mark generation as failed
        try:
            from app.db.engine import get_db_session
            from app.models.task import Task
            with get_db_session() as session:
                task = session.get(Task, task_id)
                if task:
                    task.assignment_generation_status = "failed"
                    task.generation_error = str(exc)[:500]
                    session.commit()
        except Exception:
            logger.exception("Failed to mark generation_error for task %s", task_id)

        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.task_assignment_tasks.backfill_global_tasks",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def backfill_global_tasks(self) -> dict:
    """
    One-shot backfill: find all tasks with assignment_scope='all' that have
    assignment_generation_status != 'completed' (or no assignments at all),
    and dispatch generate_bulk_assignments for each.
    """
    try:
        from sqlalchemy import select, func
        from app.db.engine import get_db_session
        from app.models.task import Task
        from app.models.task_workflow import TaskAssignment

        with get_db_session() as session:
            # Find global tasks that may need backfilling
            tasks = session.execute(
                select(Task.id, Task.org_id).where(
                    Task.assignment_scope == "all",
                )
            ).all()

        dispatched = 0
        for task_id, org_id in tasks:
            generate_bulk_assignments.delay(task_id, org_id)
            dispatched += 1

        logger.info("Backfill dispatched %d global task generation jobs.", dispatched)
        return {"status": "dispatched", "count": dispatched}

    except Exception as exc:
        logger.exception("Backfill global tasks failed")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.task_assignment_tasks.generate_enrollment_assignments",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def generate_enrollment_assignments(self, learner_id: str, org_id: int) -> dict:
    """
    When a new learner enrolls, create TaskAssignment rows for all
    active global tasks (assignment_scope='all') in their org.

    Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
    """
    try:
        from sqlalchemy import select, text
        from app.db.engine import get_db_session, is_postgres_dsn
        from app.models.task import Task

        with get_db_session() as session:
            # Find all active global tasks in the org
            global_tasks = session.execute(
                select(Task.id).where(
                    Task.org_id == org_id,
                    Task.assignment_scope == "all",
                    # Removed the assignment_generation_status filter to prevent race conditions 
                    # where learners enroll exactly while a task is being generated.
                )
            ).scalars().all()

        if not global_tasks:
            return {"status": "no_global_tasks", "created": 0}

        now = datetime.now(timezone.utc)
        total_created = 0

        with get_db_session() as session:
            if is_postgres_dsn():
                from sqlalchemy.dialects.postgresql import insert
                from app.models.task_workflow import TaskAssignment
                
                values = [
                    {
                        "task_id": tid,
                        "learner_id": learner_id,
                        "status": "assigned",
                        "assigned_at": now,
                        "org_id": org_id,
                    }
                    for tid in global_tasks
                ]
                stmt = insert(TaskAssignment).values(values)
                stmt = stmt.on_conflict_do_nothing(index_elements=['task_id', 'learner_id'])
                result = session.execute(stmt)
                total_created = result.rowcount
            else:
                from app.models.task_workflow import TaskAssignment
                for tid in global_tasks:
                    try:
                        with session.begin_nested():
                            assignment = TaskAssignment(
                                task_id=tid,
                                learner_id=learner_id,
                                status="assigned",
                                assigned_at=now,
                                org_id=org_id,
                            )
                            session.add(assignment)
                        total_created += 1
                    except Exception:
                        continue
            session.commit()

        logger.info(
            "Enrollment assignments: created %d for learner %s in org %d.",
            total_created, learner_id, org_id,
        )
        return {"status": "completed", "created": total_created}

    except Exception as exc:
        logger.exception("Enrollment assignment generation failed for learner %s", learner_id)
        raise self.retry(exc=exc)
