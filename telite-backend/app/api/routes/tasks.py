from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import TokenData, get_current_user, require_admin, resolve_org_scope
from app.core.rbac import validate_task_access
from sqlalchemy.orm import Session
from app.db.engine import db_session
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.repositories.audit_repo import AuditRepository
from app.core.rbac import ROLE_PERMISSIONS, Permission


task_router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskPayload(BaseModel):
    title: str
    description: str | None = ""
    assigned_label: str
    assigned_to_user_id: str | None = None
    assignment_scope: str = "individual"
    category_slug: str = "ats"
    due_at: str | None = None
    status: str = "pending"
    notes: str | None = ""
    is_cross_category: bool = False


@task_router.get("")
def get_tasks(
    category_slug: str | None = Query(default=None),
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    viewer = user_repo.get_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    if current_user.role == "category_admin" or Permission.CAT_MANAGE_TASKS in ROLE_PERMISSIONS.get(current_user.role, set()):
        category_slug = current_user.category_scope
    scoped_org_id = resolve_org_scope(current_user, org_id)
    
    task_repo = TaskRepository(db)
    # The viewer filter logic for list_tasks:
    # If learner, show assigned to them or 'all'.
    # Otherwise just show all in category/org.
    assigned_to = viewer.id if viewer.role in ["learner", "student", "employee", "intern"] else None
    
    tasks = task_repo.list_by_org(
        org_id=scoped_org_id, 
        category_slug=category_slug,
        assigned_to=assigned_to
    )
    return {"tasks": tasks}


@task_router.post("")
def post_task(
    body: TaskPayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        validate_task_access(current_user, actor.org_id, body.category_slug)
        task_repo = TaskRepository(db)
        task = task_repo.create_task(
            org_id=actor.org_id,
            assigned_by=actor.id,
            **body.model_dump()
        )
        AuditRepository(db).log_action(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action="task.create",
            target_type="task",
            target_id=task.id,
            org_id=actor.org_id,
            message=f"Created task: {task.title}",
        )
        db.commit()
        return task
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@task_router.patch("/{task_id}")
def patch_task(
    task_id: str,
    body: TaskPayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        validate_task_access(current_user, actor.org_id, body.category_slug)
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        task = task_repo.update_task(task, **body.model_dump())
        AuditRepository(db).log_action(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action="task.update",
            target_type="task",
            target_id=task.id,
            org_id=actor.org_id,
            message=f"Updated task: {task.title}",
        )
        db.commit()
        return task
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@task_router.delete("/{task_id}")
def remove_task(
    task_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_org_id = task.org_id or actor.org_id
    validate_task_access(current_user, task_org_id, task.category_slug)

    try:
        task_repo.delete_task(task)
        AuditRepository(db).log_action(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action="task.delete",
            target_type="task",
            target_id=task_id,
            org_id=task_org_id,
            message=f"Deleted task: {task.title}",
        )
        db.commit()
        return {"status": "success", "message": "Task deleted successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@task_router.post("/{task_id}/submit")
def mark_task_submitted(
    task_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    if actor.role not in ["learner", "student", "employee", "intern"] or not actor.is_active:
        raise HTTPException(status_code=403, detail="Active learner session required")
    try:
        task_repo = TaskRepository(db)
        task = task_repo.get_by_id(task_id)
        if not task:
            raise ValueError("Task not found")
        task = task_repo.submit_task(task)
        AuditRepository(db).log_action(
            actor_id=actor.id,
            actor_name=actor.full_name,
            action="task.submit",
            target_type="task",
            target_id=task_id,
            org_id=actor.org_id,
            message=f"Submitted task: {task.title}",
        )
        db.commit()
        return task
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
