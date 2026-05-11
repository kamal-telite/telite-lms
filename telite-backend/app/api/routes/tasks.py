from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import TokenData, get_current_user, require_admin, resolve_org_scope
from app.services.store import (
    create_or_update_task,
    delete_task,
    ensure_category_access,
    fetch_user_by_id,
    is_category_admin_role,
    is_learner_role,
    list_tasks,
    submit_task,
)


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
):
    viewer = fetch_user_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"tasks": list_tasks(category_slug=category_slug, viewer=viewer, org_id=scoped_org_id)}


@task_router.post("")
def post_task(
    body: TaskPayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, body.category_slug)
        return create_or_update_task(body.model_dump(), actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@task_router.patch("/{task_id}")
def patch_task(
    task_id: str,
    body: TaskPayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, body.category_slug)
        return create_or_update_task(body.model_dump(), actor, task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@task_router.delete("/{task_id}")
def remove_task(
    task_id: str,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        return delete_task(task_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@task_router.post("/{task_id}/submit")
def mark_task_submitted(
    task_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    if not is_learner_role(actor["role"]):
        raise HTTPException(status_code=403, detail="Learner access required")
    try:
        return submit_task(task_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
