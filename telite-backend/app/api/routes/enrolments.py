from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
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
from app.services.user_provisioning import UserProvisioningService
from app.services.bulk_enrollment_service import BulkEnrollmentService
from app.services.enrollment_service import (
    EnrollmentPermissionError,
    EnrollmentService,
    EnrollmentServiceError,
)
from datetime import datetime, timezone
import uuid
import json


enrol_router = APIRouter(prefix="/enrol", tags=["Enrollment"])
v1_enrol_router = APIRouter(prefix="/enrol", tags=["Enrollment"])

# DEPRECATED Phase O-1:
# The legacy /enrol/* routes below are retained only for backward-compatible
# routing visibility while native onboarding transitions to /api/v1/enrol/*.
# Do not add new behavior here. New enrollment workflows must use
# EnrollmentService + UserProvisioningService through v1_enrol_router.

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
    
    from app.repositories.progress_repo import ProgressRepository
    from app.models.course_progress import CourseProgress

    if user:
        if user.org_id is not None and user.org_id != req_org_id:
            raise ValueError("This user belongs to another organization.")
        user = user_repo.update(
            user,
            category_scope=req.category_slug,
            role='learner',
            enrollment_type=req.request_type,
            is_active=True,
        )
    else:
        provision_svc = UserProvisioningService(db)
        user = provision_svc._provision_identity(
            email=req.email,
            username=req.email.split("@")[0] + str(uuid.uuid4())[:4], # Fallback username
            full_name=req.full_name,
            role="learner",
            org_id=req_org_id,
            password=get_default_learner_password(),
            category_scope=req.category_slug,
            invited_via="self_enrollment",
            enrollment_type=req.request_type,
        )
        
    # Create CourseProgress records
    progress_repo = ProgressRepository(db)
    for course in courses:
        cp = CourseProgress(
            user_id=user.id,
            course_id=course.id,
            org_id=req_org_id,
            status="not_started",
            completion_percentage=0.0,
            time_spent_seconds=0
        )
        progress_repo.upsert_course_progress(cp)
    
    req = enrol_repo.approve(req, reviewed_by=actor.id)
    
    AuditRepository(db).log_action(
        actor_id=actor.id,
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



class SelfEnrollmentPayload(BaseModel):
    full_name: str
    email: str
    category_slug: str


class RejectPayload(BaseModel):
    reason: str | None = None


class BatchApprovePayload(BaseModel):
    request_ids: list[str] = Field(default_factory=list)




class BulkExecutePayload(BaseModel):
    rows: list[dict]

class ManualEnrollmentPayload(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    course_ids: list[str] = Field(default_factory=list)
    enrollment_type: str = Field(default="manual", max_length=50)
    note: str | None = Field(default=None, max_length=2000)
    category_slug: str | None = None


@v1_enrol_router.post("/manual")
def manual_enrollment(
    body: ManualEnrollmentPayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    try:
        result = EnrollmentService(db).manual_enroll(
            actor_token=current_user,
            full_name=body.full_name,
            email=body.email,
            course_ids=body.course_ids,
            enrollment_type=body.enrollment_type or "manual",
            note=body.note,
        )
        db.commit()

        # Dispatch Celery hook after transaction commits
        try:
            from app.workers.task_assignment_tasks import generate_enrollment_assignments
            generate_enrollment_assignments.delay(result.user.id, current_user.org_id)
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to dispatch global task assignment for learner %s", result.user.id
            )

        return result.to_dict()
    except EnrollmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EnrollmentServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@v1_enrol_router.post("/bulk/preview")
async def bulk_enroll_preview(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        service = BulkEnrollmentService(db)
        preview_rows = service.parse_and_validate_csv(content_str, current_user)
        return {"preview": [r.to_dict() for r in preview_rows]}
    except EnrollmentPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@v1_enrol_router.post("/bulk/execute")
def bulk_enroll_execute(
    body: BulkExecutePayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    try:
        service = BulkEnrollmentService(db)
        result = service.execute_batch(body.rows, current_user)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc




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



@enrol_router.post("/self")
def post_self_enrollment(
    body: SelfEnrollmentPayload,
):
    # DEPRECATED Phase O-1: self-signup enrollment is superseded by native
    # invitation/manual enrollment flows. Retained temporarily; do not extend.
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
    # DEPRECATED Phase O-1: legacy request listing is superseded by native
    # repository-backed enrollment workflows and should be migrated before use.
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
    # DEPRECATED Phase O-1: legacy approval helper path is superseded by
    # EnrollmentService/UserProvisioningService-backed workflows.
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
    # DEPRECATED Phase O-1: legacy rejection helper path is retained only until
    # pending enrollment request management is migrated to native repositories.
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
    # DEPRECATED Phase O-1: legacy batch approval helper path is retained only
    # until request management is migrated to native repository/service code.
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Org-scope validation: ensure all request IDs belong to actor's org
    actor_org_id = actor.get("org_id") or actor.get("organization_id")
    if not current_user.is_platform_admin:
        ensure_org_access(current_user, actor_org_id)

    key = _rate_key("enrol-approve-batch", f"{actor['id']}:{_client_ip(request)}")
    retry_after = is_limited(
        key,
        limit=ENROL_BATCH_APPROVE_LIMIT,
        window_seconds=ENROL_BATCH_APPROVE_WINDOW_SECONDS,
    )
    if retry_after is not None:
        _raise_rate_limit(retry_after)
    record_attempt(key, window_seconds=ENROL_BATCH_APPROVE_WINDOW_SECONDS)
    return approve_enrollment_requests_batch(body.request_ids, actor)
