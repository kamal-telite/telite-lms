from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.auth import TokenData, require_admin, resolve_org_scope, ensure_org_access
from app.core.rate_limiter import is_limited, record_attempt
from app.core.rbac import validate_enrollment_access
from app.services.store import (
    approve_enrollment_request,
    approve_enrollment_requests_batch,
    create_manual_enrollment,
    create_self_enrollment_request,
    ensure_category_access,
    fetch_enrollment_request_by_id,
    fetch_user_by_id,
    is_category_admin_role,
    list_enrollment_requests,
    reject_enrollment_request,
)


enrol_router = APIRouter(prefix="/enrol", tags=["Enrollment"])

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

    # Validate that the request belongs to the actor's org
    enrol_req = fetch_enrollment_request_by_id(request_id)
    if not enrol_req:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    validate_enrollment_access(current_user, enrol_req.get("org_id") or actor.get("org_id") or 1)

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

    # Validate that the request belongs to the actor's org
    enrol_req = fetch_enrollment_request_by_id(request_id)
    if not enrol_req:
        raise HTTPException(status_code=404, detail="Enrollment request not found")
    validate_enrollment_access(current_user, enrol_req.get("org_id") or actor.get("org_id") or 1)

    try:
        return reject_enrollment_request(request_id, actor, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@enrol_router.post("/requests/approve-batch")
def approve_batch(
    body: BatchApprovePayload,
    request: Request,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    # Org-scope validation: ensure all request IDs belong to actor's org
    actor_org_id = actor.get("org_id") or actor.get("organization_id") or 1
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
