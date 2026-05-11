from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import TokenData, require_admin, resolve_org_scope
from app.services.store import (
    approve_enrollment_request,
    approve_enrollment_requests_batch,
    create_manual_enrollment,
    create_self_enrollment_request,
    ensure_category_access,
    fetch_user_by_id,
    is_category_admin_role,
    list_enrollment_requests,
    reject_enrollment_request,
)


enrol_router = APIRouter(prefix="/enrol", tags=["Enrollment"])


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


@enrol_router.post("/manual")
def post_manual_enrollment(
    body: ManualEnrollmentPayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, body.category_slug)
        return create_manual_enrollment(body.model_dump(), actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@enrol_router.post("/self")
def post_self_enrollment(
    body: SelfEnrollmentPayload,
):
    try:
        return create_self_enrollment_request(body.model_dump(), None)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@enrol_router.get("/requests")
def get_enrollment_requests(
    category_slug: str | None = Query(default=None),
    status: str | None = Query(default=None),
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
    statuses = [status] if status else None
    return {"requests": list_enrollment_requests(category_slug=category_slug, statuses=statuses, org_id=scoped_org_id)}


@enrol_router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: str,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        return approve_enrollment_request(request_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@enrol_router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: str,
    body: RejectPayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        return reject_enrollment_request(request_id, actor, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@enrol_router.post("/requests/approve-batch")
def approve_batch(
    body: BatchApprovePayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return approve_enrollment_requests_batch(body.request_ids, actor)
