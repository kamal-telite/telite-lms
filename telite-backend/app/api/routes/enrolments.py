from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.auth import TokenData, require_admin, resolve_org_scope, ensure_org_access
from app.core.rate_limiter import is_limited, record_attempt
from app.core.rbac import validate_enrollment_access
from sqlalchemy.orm import Session
from app.db.engine import db_session
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.audit_repo import AuditRepository
from app.core.password_utils import hash_password, get_default_learner_password
from app.core.rbac import ROLE_PERMISSIONS, Permission
from datetime import datetime, timezone
import uuid
import json


enrol_router = APIRouter(prefix="/enrol", tags=["Enrollment"])

def _default_progress(courses):
    return [
        {
            "course_id": c.id,
            "progress": 0,
            "status": "not_started",
            "current_lesson": None,
        }
        for c in courses
    ]

def _slugify(text):
    return text.lower().replace(" ", "-")

def _approve_request(db: Session, request_id: str, actor):
    enrol_repo = EnrollmentRepository(db)
    req = enrol_repo.get_by_id(request_id)
    if not req:
        raise ValueError("Enrollment request not found.")
    if req.status != "pending":
        raise ValueError("Only pending requests can be approved.")
        
    req_org_id = req.org_id
    if not actor.is_platform_admin and actor.org_id != req_org_id:
        raise ValueError("You do not have permission to approve users outside your organization.")

    course_repo = CourseRepository(db)
    courses = course_repo.list_by_org(req_org_id, category_slug=req.category_slug, status="active")
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(req.email)
    
    if user:
        if user.org_id is not None and user.org_id != req_org_id:
            raise ValueError("This user belongs to another organization.")
        user = user_repo.update_user(
            user,
            category_scope=req.category_slug,
            role='learner',
            enrollment_type=req.request_type,
            is_active=True,
            current_course_id=courses[0].id if courses else None,
            total_courses=len(courses),
            course_progress_json=json.dumps(_default_progress(courses)),
        )
    else:
        user = user_repo.create_user(
            email=req.email,
            full_name=req.full_name,
            role="learner",
            org_id=req_org_id,
            password="TMP",
            category_scope=req.category_slug,
            enrollment_type=req.request_type,
            current_course_id=courses[0].id if courses else None,
            total_courses=len(courses),
            course_progress_json=json.dumps(_default_progress(courses)),
        )
        user.password_hash = hash_password(get_default_learner_password())
    
    req = enrol_repo.approve(req, reviewed_by=actor.id)
    
    AuditRepository(db).write(
        actor_user_id=actor.id,
        actor_name=actor.full_name,
        action="enrollment.approve",
        target_type="enrollment_request",
        target_id=req.id,
        org_id=req_org_id,
        message=f"Approved enrollment request for {req.email}",
    )
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.org_id,
        "category_slug": req.category_slug,
        "request_id": req.id,
    }


ENROL_BATCH_APPROVE_LIMIT = int(os.getenv("TELITE_ENROL_BATCH_APPROVE_LIMIT", "5"))
ENROL_BATCH_APPROVE_WINDOW_SECONDS = int(os.getenv("TELITE_ENROL_BATCH_APPROVE_WINDOW_SECONDS", "600"))


class ManualEnrollmentPayload(BaseModel):
    full_name: str
    email: str
    category_slug: str
    course_ids: list[str] = Field(default_factory=list)
    enrollment_type: str = "manual"
    note: str | None = ""
    password: str | None = None


class SelfEnrollmentPayload(BaseModel):
    full_name: str
    email: str
    category_slug: str


class RejectPayload(BaseModel):
    reason: str | None = None


class BatchApprovePayload(BaseModel):
    request_ids: list[str] = Field(default_factory=list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_key(namespace: str, raw_value: str) -> str:
    normalized = raw_value.strip().lower() or "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def _raise_rate_limit(retry_after: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please try again later.",
        headers={"Retry-After": str(retry_after)},
    )


@enrol_router.post("/manual")
def post_manual_enrollment(
    body: ManualEnrollmentPayload,
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, body.category_slug)
        return create_manual_enrollment(body.model_dump(), actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@enrol_router.post("/self")
def post_self_enrollment(
    body: SelfEnrollmentPayload,
):
    try:
        return create_self_enrollment_request(body.model_dump(), None)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@enrol_router.get("/requests")
def get_enrollment_requests(
    category_slug: str | None = Query(default=None),
    status: str | None = Query(default=None),
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
    statuses = [status] if status else None
    return {"requests": list_enrollment_requests(category_slug=category_slug, statuses=statuses, org_id=scoped_org_id)}


@enrol_router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: str,
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Validate that the request belongs to the actor's org
    enrol_req = fetch_enrollment_request_by_id(request_id)
    if not enrol_req:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    validate_enrollment_access(current_user, enrol_req.get("org_id") or actor.get("org_id"))

    try:
        return approve_enrollment_request(request_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@enrol_router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: str,
    body: RejectPayload,
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Validate that the request belongs to the actor's org
    enrol_req = fetch_enrollment_request_by_id(request_id)
    if not enrol_req:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    validate_enrollment_access(current_user, enrol_req.get("org_id") or actor.get("org_id"))

    try:
        return reject_enrollment_request(request_id, actor, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@enrol_router.post("/requests/approve-batch")
def approve_batch(
    body: BatchApprovePayload,
    request: Request,
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    actor = UserRepository(db).get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Org-scope validation: ensure all request IDs belong to actor's org
    actor_org_id = actor.org_id
    if not current_user.is_platform_admin:
        ensure_org_access(current_user, actor_org_id)

    key = _rate_key("enrol-approve-batch", f"{actor.id}:{_client_ip(request)}")
    retry_after = is_limited(
        key,
        limit=ENROL_BATCH_APPROVE_LIMIT,
        window_seconds=ENROL_BATCH_APPROVE_WINDOW_SECONDS,
    )
    if retry_after is not None:
        _raise_rate_limit(retry_after)
    record_attempt(key, window_seconds=ENROL_BATCH_APPROVE_WINDOW_SECONDS)
    
    approved_count = 0
    enrol_repo = EnrollmentRepository(db)
    for req_id in body.request_ids:
        try:
            _approve_request(db, req_id, actor)
            approved_count += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
            
    import uuid
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    
    AuditRepository(db).write(
        actor_user_id=actor.id,
        actor_name=actor.full_name,
        action="enrol.approve_batch",
        target_type="job",
        target_id=job_id,
        org_id=actor_org_id,
        message=f"Batch approved {approved_count} requests",
        result="success",
    )
    
    db.commit()
    return {"approved": approved_count, "job_id": job_id, "failed": len(body.request_ids) - approved_count, "requested": len(body.request_ids)}
