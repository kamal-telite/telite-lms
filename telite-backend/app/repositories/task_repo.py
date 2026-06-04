"""
TaskRepository — task data access.

Replaces: list_tasks, fetch_task_by_id, create_or_update_task,
delete_task, submit_task.
"""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.repositories.base_repo import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def list_by_org(
        self,
        org_id: int,
        *,
        category_slug: str | None = None,
        assigned_to: str | None = None,
        status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Task]:
        stmt = select(Task).where(Task.org_id == org_id)
        if category_slug:
            stmt = stmt.where(
                or_(Task.category_slug == category_slug, Task.is_cross_category.is_(True))
            )
        if assigned_to:
            stmt = stmt.where(
                or_(
                    Task.assigned_to_user_id == assigned_to,
                    Task.assignment_scope == "all",
                )
            )
        if status:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        return self.session.execute(stmt).scalars().all()

    def create_task(
        self,
        *,
        title: str,
        category_slug: str,
        org_id: int,
        assigned_label: str,
        assigned_by: str | None = None,
        **extra: Any,
    ) -> Task:
        from datetime import datetime
        task = Task(
            id=f"task-{uuid.uuid4().hex[:10]}",
            title=title.strip(),
            category_slug=category_slug,
            org_id=org_id,
            assigned_label=assigned_label,
            assigned_by=assigned_by,
            status="pending",
            **extra,
        )
        self.session.add(task)
        self.session.flush()
        return task

    def update_task(self, task: Task, **fields: Any) -> Task:
        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self.session.flush()
        return task

    def submit_task(self, task: Task) -> Task:
        task.status = "submitted"
        self.session.flush()
        return task

    def delete_task(self, task: Task) -> None:
        self.session.delete(task)
        self.session.flush()
