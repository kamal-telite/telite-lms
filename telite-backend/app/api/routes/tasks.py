from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import TokenData, get_current_user, require_admin, resolve_org_scope
from app.core.rbac import validate_task_access
from sqlalchemy.orm import Session
from app.db.engine import apply_tenant_context, db_session
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
from app.repositories.audit_repo import AuditRepository
from app.repositories.notification_repo import NotificationRepository
from app.core.rbac import ROLE_PERMISSIONS, Permission


task_router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = logging.getLogger(__name__)


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


class TaskSubmissionPayload(BaseModel):
    submission_notes: str | None = ""
    attachment_url: str | None = None
    github_url: str | None = None
    external_url: str | None = None


class TaskReviewPayload(BaseModel):
    action: str = Field(pattern="^(approve|request_revision|reject)$")
    review_notes: str | None = ""


def _write_audit_safely(
    db: Session,
    *,
    org_id: int,
    actor_user_id: str | None,
    actor_name: str,
    action: str,
    target_type: str,
    target_id: str,
    message: str,
) -> None:
    try:
        apply_tenant_context(db, org_id)
        AuditRepository(db).write(
            org_id=org_id,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            message=message,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Audit logging failed for %s %s", target_type, target_id)


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

    task_payloads = task_repo.list_assignment_payloads_by_org(
        org_id=scoped_org_id, 
        category_slug=category_slug,
        assigned_to=assigned_to
    )
    if not task_payloads and not assigned_to:
        task_payloads = [task.to_dict() for task in task_repo.list_by_org(org_id=scoped_org_id, category_slug=category_slug)]
    return {"tasks": task_payloads}


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
        assignment = None
        if body.assigned_to_user_id:
            assignment = task_repo.create_assignment(task=task, learner_id=body.assigned_to_user_id)
            NotificationRepository(db).create(
                user_id=body.assigned_to_user_id,
                org_id=actor.org_id,
                title="New task assigned",
                body=f"New task assigned: {task.title}",
                notif_type="task_assigned",
                metadata={"task_id": task.id, "assignment_id": assignment.id},
            )
        response = task_repo.task_payload(task, assignment)
        db.commit()
        _write_audit_safely(
            db,
            org_id=actor.org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="task.create",
            target_type="task",
            target_id=task.id,
            message=f"Created task: {task.title}",
        )
        return response
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
        assignment = task_repo.get_assignment(task.id, body.assigned_to_user_id)
        if assignment:
            assignment.status = task_repo.assignment_status(body.status)
        response = task_repo.task_payload(task, assignment)
        db.commit()
        _write_audit_safely(
            db,
            org_id=actor.org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="task.update",
            target_type="task",
            target_id=task.id,
            message=f"Updated task: {task.title}",
        )
        return response
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
        task_title = task.title
        task_repo.delete_task(task)
        db.commit()
        _write_audit_safely(
            db,
            org_id=task_org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="task.delete",
            target_type="task",
            target_id=task_id,
            message=f"Deleted task: {task_title}",
        )
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
        assignment = task_repo.get_assignment(task_id, actor.id)
        if not assignment:
            raise ValueError("Task assignment not found")
        task_repo.submit_assignment(assignment)
        response = task_repo.task_payload(task, assignment)
        task.status = task_repo.task_status(assignment.status)
        db.commit()
        _write_audit_safely(
            db,
            org_id=actor.org_id,
            actor_user_id=actor.id,
            actor_name=actor.full_name,
            action="task.submit",
            target_type="task",
            target_id=task_id,
            message=f"Submitted task: {task.title}",
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@task_router.post("/{task_id}/start")
def start_task(
    task_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor or actor.role not in ["learner", "student", "employee", "intern"] or not actor.is_active:
        raise HTTPException(status_code=403, detail="Active learner session required")
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    assignment = task_repo.get_assignment(task_id, actor.id)
    if not task or not assignment:
        raise HTTPException(status_code=404, detail="Task assignment not found")
    assignment = task_repo.start_assignment(assignment)
    task.status = task_repo.task_status(assignment.status)
    response = task_repo.task_payload(task, assignment)
    db.commit()
    return response


@task_router.post("/{task_id}/submit-work")
def submit_task_work(
    task_id: str,
    body: TaskSubmissionPayload,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor or actor.role not in ["learner", "student", "employee", "intern"] or not actor.is_active:
        raise HTTPException(status_code=403, detail="Active learner session required")
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    assignment = task_repo.get_assignment(task_id, actor.id)
    if not task or not assignment:
        raise HTTPException(status_code=404, detail="Task assignment not found")
    task_repo.submit_assignment(
        assignment,
        submission_notes=body.submission_notes,
        attachment_url=body.attachment_url,
        github_url=body.github_url,
        external_url=body.external_url,
    )
    task.status = task_repo.task_status(assignment.status)
    response = task_repo.task_payload(task, assignment)
    db.commit()
    return response


@task_router.post("/{task_id}/review")
def review_task(
    task_id: str,
    body: TaskReviewPayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    task_repo = TaskRepository(db)
    task = task_repo.get_by_id(task_id)
    assignment = task_repo.get_assignment(task_id)
    if not task or not assignment:
        raise HTTPException(status_code=404, detail="Task assignment not found")
    validate_task_access(current_user, task.org_id, task.category_slug)
    if assignment.status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted tasks can be reviewed")
    review_status = {
        "approve": "approved",
        "request_revision": "revision_requested",
        "reject": "rejected",
    }[body.action]
    task_repo.review_assignment(
        assignment,
        review_status=review_status,
        review_notes=body.review_notes,
        reviewed_by=actor.id,
    )
    task.status = task_repo.task_status(assignment.status)
    if assignment.learner_id:
        title = "Task approved" if review_status == "approved" else "Revision requested" if review_status == "revision_requested" else "Task rejected"
        body_text = "Your task has been approved." if review_status == "approved" else f"Revision requested on your task: {task.title}" if review_status == "revision_requested" else f"Your task was rejected: {task.title}"
        NotificationRepository(db).create(
            user_id=assignment.learner_id,
            org_id=task.org_id,
            title=title,
            body=body_text,
            notif_type=f"task_{review_status}",
            metadata={"task_id": task.id, "assignment_id": assignment.id},
        )
    response = task_repo.task_payload(task, assignment)
    db.commit()
    return response
