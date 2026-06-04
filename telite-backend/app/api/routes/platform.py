"""Platform Admin API routes — /api/platform/*

All endpoints require is_platform_admin=1 on the authenticated user.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.api.auth import TokenData, TokenResponse, issue_login_response, require_platform_admin
from app.integrations.moodle_events import publish_moodle_event, publish_reconciliation_event
from app.services.auth_rate_limiter import is_limited, record_attempt
from app.services.email import send_invitation_email, send_password_reset_email
from app.services.store import (
    ADMIN_ROLES,
    SQL_LEARNER_ROLES,
    accept_invitation_signup,
    create_invitation,
    create_platform_alert_rule,
    create_platform_organization,
    create_password_reset_token,
    export_audit_logs_csv,
    export_platform_analytics_csv,
    fetch_user_by_id,
    get_all_org_feature_flags,
    get_moodle_sync_report,
    get_conn,
    get_organization,
    get_platform_org_analytics_detail,
    list_admins,
    list_platform_admin_directory,
    list_audit_logs,
    list_moodle_sync_logs,
    list_moodle_tenants,
    list_organizations,
    list_pending_invitations,
    platform_analytics_overview,
    record_invitation_delivery,
    record_invitation_resend,
    record_password_reset_delivery,
    revoke_invitation,
    revoke_sessions_for_user,
    toggle_feature_flag,
    update_organization,
    validate_invitation,
    write_platform_audit,
    now_date,
)

logger = logging.getLogger("telite.platform")

PLATFORM_ADMIN_INVITE_LIMIT = int(os.getenv("TELITE_PLATFORM_ADMIN_INVITE_LIMIT", "5"))
PLATFORM_ADMIN_INVITE_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_ADMIN_INVITE_WINDOW_SECONDS", "600"))
PLATFORM_PASSWORD_RESET_LIMIT = int(os.getenv("TELITE_PLATFORM_PASSWORD_RESET_LIMIT", "5"))
PLATFORM_PASSWORD_RESET_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_PASSWORD_RESET_WINDOW_SECONDS", "900"))
PLATFORM_MOODLE_SYNC_ORG_LIMIT = int(os.getenv("TELITE_PLATFORM_MOODLE_SYNC_ORG_LIMIT", "3"))
PLATFORM_MOODLE_SYNC_ORG_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_MOODLE_SYNC_ORG_WINDOW_SECONDS", "600"))
PLATFORM_MOODLE_SYNC_ALL_LIMIT = int(os.getenv("TELITE_PLATFORM_MOODLE_SYNC_ALL_LIMIT", "2"))
PLATFORM_MOODLE_SYNC_ALL_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_MOODLE_SYNC_ALL_WINDOW_SECONDS", "600"))
PLATFORM_ANALYTICS_ALERT_LIMIT = int(os.getenv("TELITE_PLATFORM_ANALYTICS_ALERT_LIMIT", "10"))
PLATFORM_ANALYTICS_ALERT_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_ANALYTICS_ALERT_WINDOW_SECONDS", "600"))

platform_router = APIRouter(prefix="/api/platform", tags=["Platform Admin"])


# ── Auth dependency ──────────────────────────────────────────────────────────


# ── Pydantic models ──────────────────────────────────────────────────────────


class CreateOrgPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: str = Field(..., pattern=r"^(college|company)$")
    domain: str = Field(..., min_length=3)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$")
    super_admin_email: str | None = None
    moodle_setup: str = Field(default="manual", pattern=r"^(auto|manual)$")


class UpdateOrgPayload(BaseModel):
    name: str | None = None
    domain: str | None = None
    slug: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|suspended)$")
    logo_url: str | None = None


class UpdateStatusPayload(BaseModel):
    status: str = Field(..., pattern=r"^(active|inactive|suspended)$")


class InviteAdminPayload(BaseModel):
    org_id: int
    email: str = Field(..., min_length=5)
    role: str = Field(..., min_length=2)


class AcceptInvitationPayload(BaseModel):
    token: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=200)
    password: str = Field(..., min_length=8)


class ToggleFeaturePayload(BaseModel):
    feature_key: str
    is_enabled: bool


class UpdateAdminStatusPayload(BaseModel):
    status: str = Field(..., pattern=r"^(active|suspended)$")


class CreateAnalyticsAlertPayload(BaseModel):
    org_id: int
    metric: str = Field(..., min_length=3)
    threshold: float = Field(..., ge=0)
    channel: str = Field(..., min_length=3)


# ── Helper: get client IP ────────────────────────────────────────────────────


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


def _enforce_endpoint_rate_limit(*, namespace: str, subject: str, limit: int, window_seconds: int) -> None:
    key = _rate_key(namespace, subject)
    retry_after = is_limited(key, limit=limit, window_seconds=window_seconds)
    if retry_after is not None:
        _raise_rate_limit(retry_after)
    record_attempt(key, window_seconds=window_seconds)


# ══════════════════════════════════════════════════════════════════════════════
#  ORGANIZATIONS
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/organizations")
def api_list_organizations(
    type: str = Query(default="all"),
    status: str = Query(default="all"),
    search: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: TokenData = Depends(require_platform_admin),
):
    return list_organizations(
        org_type=type, status=status, search=search or None, page=page, limit=limit
    )


@platform_router.post("/organizations", status_code=201)
def api_create_organization(
    payload: CreateOrgPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    try:
        creation = create_platform_organization(
            name=payload.name,
            org_type=payload.type,
            domain=payload.domain,
            slug=payload.slug,
            actor_id=admin.id,
            super_admin_email=payload.super_admin_email,
            moodle_setup=payload.moodle_setup,
        )
        org = creation["org"]
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    invitation_sent = creation["invitation_sent"]
    if creation.get("invitation") and payload.super_admin_email:
        delivered = send_invitation_email(
            to_email=creation["invitation"]["email"],
            org_name=org["name"],
            role=creation["invitation"]["role"],
            token=creation["invitation"]["token"],
            expires_at=creation["invitation"]["expires_at"],
        )
        invitation = record_invitation_delivery(
            creation["invitation"]["id"],
            delivered=delivered,
            error=None if delivered else "SMTP not configured or invitation email delivery failed",
        )
        creation["invitation"] = invitation
        invitation_sent = delivered

    if payload.moodle_setup == "auto":
        creation["moodle_sync"] = publish_moodle_event(
            "organization.moodle_setup",
            org_id=org["id"],
            category_identifier=f"org:{org['id']}",
            payload={"org_id": org["id"], "name": payload.name},
        )

    write_platform_audit(
        action="org.create",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org["id"],
        target_type="org",
        target_id=str(org["id"]),
        message=f"Created organization '{payload.name}' ({payload.type})",
        ip_address=_client_ip(request),
        metadata={"domain": payload.domain, "moodle_setup": payload.moodle_setup},
    )

    return {
        "org": org,
        "invitation_sent": invitation_sent,
        "moodle_sync": creation.get("moodle_sync"),
    }


@platform_router.get("/organizations/{org_id}")
def api_get_organization(
    org_id: int,
    admin: TokenData = Depends(require_platform_admin),
):
    org = get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@platform_router.patch("/organizations/{org_id}")
def api_update_organization(
    org_id: int,
    payload: UpdateOrgPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    existing = get_organization(org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Organization not found")
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    try:
        org = update_organization(org_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    write_platform_audit(
        action="org.update",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org_id,
        target_type="org",
        target_id=str(org_id),
        message=f"Updated organization '{existing['name']}'",
        ip_address=_client_ip(request),
        metadata=updates,
    )
    return org


@platform_router.patch("/organizations/{org_id}/status")
def api_update_org_status(
    org_id: int,
    payload: UpdateStatusPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    existing = get_organization(org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Organization not found")
    org = update_organization(org_id, {"status": payload.status})
    action = "org.suspend" if payload.status == "suspended" else "org.activate"
    write_platform_audit(
        action=action,
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org_id,
        target_type="org",
        target_id=str(org_id),
        message=f"Set organization '{existing['name']}' to {payload.status}",
        severity="WARN" if payload.status == "suspended" else "INFO",
        ip_address=_client_ip(request),
    )
    return org


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN CONTROL
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/admins")
def api_list_admins(
    role: str = Query(default="all"),
    status: str = Query(default="all"),
    org_id: int | None = Query(default=None),
    query: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: TokenData = Depends(require_platform_admin),
):
    """List all admin-level users + pending invitations."""
    try:
        return list_platform_admin_directory(
            role=role,
            status=status,
            org_id=org_id,
            query=query,
            page=page,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@platform_router.post("/admins/invite", status_code=201)
def api_invite_admin(
    payload: InviteAdminPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-admin-invite",
        subject=f"{admin.id}:{payload.org_id}:{_client_ip(request)}",
        limit=PLATFORM_ADMIN_INVITE_LIMIT,
        window_seconds=PLATFORM_ADMIN_INVITE_WINDOW_SECONDS,
    )
    org = get_organization(payload.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    try:
        invitation = create_invitation(
            org_id=payload.org_id,
            email=payload.email,
            role=payload.role,
            invited_by=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not invitation or "email" not in invitation:
        raise HTTPException(status_code=500, detail="Failed to create invitation record")
    delivered = send_invitation_email(
        to_email=invitation["email"],
        org_name=org["name"],
        role=invitation["role"],
        token=invitation["token"],
        expires_at=invitation["expires_at"],
    )
    invitation = record_invitation_delivery(
        invitation["id"],
        delivered=delivered,
        error=None if delivered else "SMTP not configured or invitation email delivery failed",
    )

    write_platform_audit(
        action="admin.invite",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=payload.org_id,
        target_type="user",
        target_id=payload.email,
        message=f"Invited {payload.email} as {payload.role} to {org['name']}",
        ip_address=_client_ip(request),
        metadata={"delivery_status": invitation.get("delivery_status")},
    )
    return {"invitation": invitation}


@platform_router.post("/admins/invitations/{invitation_id}/resend")
def api_resend_admin_invitation(
    invitation_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    try:
        invitation = record_invitation_resend(invitation_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Invitation not found." else 409
        raise HTTPException(status_code=status_code, detail=detail)

    delivered = send_invitation_email(
        to_email=invitation["email"],
        org_name=invitation["org_name"],
        role=invitation["role"],
        token=invitation["token"],
        expires_at=invitation["expires_at"],
    )
    org_name = invitation["org_name"]
    invitation = record_invitation_delivery(
        invitation["id"],
        delivered=delivered,
        error=None if delivered else "SMTP not configured or invitation email delivery failed",
    )
    invitation["org_name"] = org_name

    write_platform_audit(
        action="invite.resend",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=invitation["org_id"],
        target_type="invitation",
        target_id=str(invitation_id),
        message=f"Resent invitation to {invitation['email']} for {org_name}",
        ip_address=_client_ip(request),
        metadata={
            "delivery_status": invitation.get("delivery_status"),
            "resend_count": invitation.get("resend_count"),
        },
    )
    return {"invitation": invitation}


@platform_router.delete("/admins/invitations/{invitation_id}")
def api_revoke_admin_invitation(
    invitation_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    try:
        invitation = revoke_invitation(
            invitation_id,
            revoked_by=admin.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Invitation not found." else 409
        raise HTTPException(status_code=status_code, detail=detail)

    write_platform_audit(
        action="invite.revoke",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=invitation["org_id"],
        target_type="invitation",
        target_id=str(invitation_id),
        message=f"Revoked invitation for {invitation['email']} in {invitation['org_name']}",
        ip_address=_client_ip(request),
        severity="WARN",
        metadata={
            "email": invitation["email"],
            "role": invitation["role"],
            "revoked_by": invitation.get("revoked_by"),
            "revoke_reason": invitation.get("revoke_reason"),
        },
    )
    return {"invitation": invitation}


@platform_router.patch("/admins/{user_id}/status")
def api_update_admin_status(
    user_id: str,
    payload: UpdateAdminStatusPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_active = 1 if payload.status == "active" else 0
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, payload.status, user_id))
        conn.commit()
    revoked_sessions = revoke_sessions_for_user(user_id) if payload.status == "suspended" else 0
    action = "admin.suspend" if payload.status == "suspended" else "admin.activate"
    write_platform_audit(
        action=action,
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=user.get("org_id"),
        target_type="user",
        target_id=user_id,
        message=f"Set admin '{user['full_name']}' to {payload.status}",
        severity="WARN" if payload.status == "suspended" else "INFO",
        ip_address=_client_ip(request),
        metadata={"revoked_sessions": revoked_sessions},
    )
    return {"user_id": user_id, "status": payload.status, "revoked_sessions": revoked_sessions}


@platform_router.delete("/admins/{user_id}")
def api_delete_admin(
    user_id: str,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="You cannot delete your own platform admin account")
    if bool(user.get("is_platform_admin")):
        raise HTTPException(status_code=409, detail="Platform admin accounts cannot be deleted from this endpoint")
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=400, detail="Delete admin API only supports admin users")
    if not user.get("is_active"):
        raise HTTPException(status_code=409, detail="Admin has already been deleted")

    org_id = user.get("org_id")
    if org_id is not None:
        active_org_admins = [
            item for item in list_admins(org_id=org_id)
            if item.get("id") != user_id and item.get("is_active")
        ]
        if not active_org_admins:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the last active admin for this organization",
            )

    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET is_active = 0, status = ? WHERE id = ?",
            ("inactive", user_id),
        )
        conn.commit()

    revoked_sessions = revoke_sessions_for_user(user_id)
    deleted_user = fetch_user_by_id(user_id) or user

    write_platform_audit(
        action="admin.delete",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org_id,
        target_type="user",
        target_id=user_id,
        message=f"Deleted admin '{user['full_name']}'",
        severity="WARN",
        ip_address=_client_ip(request),
        metadata={
            "email": user["email"],
            "role": user["role"],
            "revoked_sessions": revoked_sessions,
        },
    )
    return {
        "user": deleted_user,
        "deleted": True,
        "revoked_sessions": revoked_sessions,
    }


@platform_router.post("/admins/{user_id}/reset-password")
def api_trigger_admin_password_reset(
    user_id: str,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-admin-password-reset",
        subject=f"{admin.id}:{user_id}:{_client_ip(request)}",
        limit=PLATFORM_PASSWORD_RESET_LIMIT,
        window_seconds=PLATFORM_PASSWORD_RESET_WINDOW_SECONDS,
    )
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not (bool(user.get("is_platform_admin")) or user.get("role") in ADMIN_ROLES):
        raise HTTPException(status_code=400, detail="Password reset is only supported for admin users")

    reset_request = create_password_reset_token(user["email"])
    if not reset_request:
        raise HTTPException(status_code=400, detail="User is inactive or password reset could not be created")

    delivered = send_password_reset_email(
        to_email=reset_request["email"],
        name=reset_request["full_name"],
        token=reset_request["token"],
        expires_at=reset_request["expires_at"],
    )
    if reset_request.get("id") is not None:
        reset_request = record_password_reset_delivery(
            reset_request["id"],
            delivered=delivered,
            error=None if delivered else "SMTP not configured or password reset email delivery failed",
        )

    write_platform_audit(
        action="admin.password_reset",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=user.get("org_id"),
        target_type="user",
        target_id=user_id,
        message=f"Triggered password reset for '{user['full_name']}'",
        ip_address=_client_ip(request),
        metadata={
            "email": user["email"],
            "delivery_status": reset_request.get("delivery_status"),
        },
    )
    return {
        "status": "reset_requested",
        "user_id": user_id,
        "email": user["email"],
        "delivery_status": reset_request.get("delivery_status"),
        "delivery_error": reset_request.get("delivery_error"),
        "delivery_attempted_at": reset_request.get("delivery_attempted_at"),
        "delivered_at": reset_request.get("delivered_at"),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/analytics/overview")
def api_analytics_overview(
    admin: TokenData = Depends(require_platform_admin),
):
    return platform_analytics_overview()


@platform_router.get("/analytics/export")
def api_export_analytics(
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    csv_content = export_platform_analytics_csv()
    filename = f"platform-analytics-{now_date()}.csv"
    write_platform_audit(
        action="analytics.export",
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="analytics",
        target_id="platform_overview",
        message="Exported platform analytics overview",
        ip_address=_client_ip(request),
        metadata={"format": "csv", "filename": filename},
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@platform_router.get("/analytics/org/{org_id}")
def api_analytics_per_org(
    org_id: int,
    days: int = Query(default=30, ge=1, le=365),
    admin: TokenData = Depends(require_platform_admin),
):
    """Per-org analytics breakdown."""
    try:
        return get_platform_org_analytics_detail(org_id, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@platform_router.post("/analytics/alerts", status_code=201)
def api_create_analytics_alert(
    payload: CreateAnalyticsAlertPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-analytics-alert",
        subject=f"{admin.id}:{payload.org_id}:{payload.metric}:{_client_ip(request)}",
        limit=PLATFORM_ANALYTICS_ALERT_LIMIT,
        window_seconds=PLATFORM_ANALYTICS_ALERT_WINDOW_SECONDS,
    )
    try:
        rule = create_platform_alert_rule(
            org_id=payload.org_id,
            metric=payload.metric,
            threshold=payload.threshold,
            channel=payload.channel,
            created_by=admin.id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Organization not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    write_platform_audit(
        action="analytics.alert.create",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=payload.org_id,
        target_type="analytics_alert",
        target_id=str(rule["id"]),
        message=f"Configured analytics alert for org {payload.org_id}: {rule['metric']} via {rule['channel']}",
        ip_address=_client_ip(request),
        metadata={
            "metric": rule["metric"],
            "threshold": rule["threshold"],
            "channel": rule["channel"],
            "is_enabled": bool(rule["is_enabled"]),
        },
    )
    return {"rule": rule}


# ══════════════════════════════════════════════════════════════════════════════
#  MOODLE SYNC
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/moodle/tenants")
def api_moodle_tenants(
    admin: TokenData = Depends(require_platform_admin),
):
    return list_moodle_tenants()


@platform_router.get("/moodle/logs")
def api_moodle_logs(
    org_id: int | None = Query(default=None),
    category_identifier: str | None = Query(default=None),
    status: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    query: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    admin: TokenData = Depends(require_platform_admin),
):
    return list_moodle_sync_logs(
        org_id=org_id,
        category_identifier=category_identifier,
        status=status,
        event_type=event_type,
        query=query,
        page=page,
        limit=limit,
    )


@platform_router.post("/moodle/sync/{org_id}")
def api_moodle_sync_org(
    org_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-moodle-sync-org",
        subject=f"{admin.id}:{org_id}:{_client_ip(request)}",
        limit=PLATFORM_MOODLE_SYNC_ORG_LIMIT,
        window_seconds=PLATFORM_MOODLE_SYNC_ORG_WINDOW_SECONDS,
    )
    org = get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    result = publish_reconciliation_event(org_id, actor_id=admin.id)
    write_platform_audit(
        action="moodle.sync",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org_id,
        target_type="moodle",
        target_id=str(org_id),
        message=f"Queued Moodle reconciliation for '{org['name']}'",
        ip_address=_client_ip(request),
        metadata=result,
    )
    return {"status": "queued", "org_id": org_id, "org_name": org["name"], "sync_job": result}


@platform_router.post("/moodle/sync-all")
def api_moodle_sync_all(
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    """Trigger sync for all active orgs with a batch summary."""
    _enforce_endpoint_rate_limit(
        namespace="platform-moodle-sync-all",
        subject=f"{admin.id}:{_client_ip(request)}",
        limit=PLATFORM_MOODLE_SYNC_ALL_LIMIT,
        window_seconds=PLATFORM_MOODLE_SYNC_ALL_WINDOW_SECONDS,
    )
    tenants = list_moodle_tenants()
    events = [
        publish_reconciliation_event(int(tenant["org_id"]), actor_id=admin.id)
        for tenant in tenants
        if tenant.get("org_id") is not None
    ]
    result = {"status": "queued", "triggered": len(events), "events": events}
    write_platform_audit(
        action="moodle.sync_all",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=None,
        target_type="moodle",
        target_id="all",
        message=f"Batch Moodle reconciliation queued for {result['triggered']} organizations",
        ip_address=_client_ip(request),
        metadata=result,
    )
    return result


@platform_router.get("/moodle/sync-status")
def api_moodle_sync_status(
    admin: TokenData = Depends(require_platform_admin),
):
    return list_moodle_tenants()


@platform_router.get("/moodle/reports/summary")
def api_moodle_report_summary(
    days: int = Query(default=30, ge=1, le=90),
    admin: TokenData = Depends(require_platform_admin),
):
    return get_moodle_sync_report(days=days)


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE FLAGS
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/features")
def api_list_features(
    admin: TokenData = Depends(require_platform_admin),
):
    return get_all_org_feature_flags()


@platform_router.patch("/features/{org_id}")
def api_toggle_feature(
    org_id: int,
    payload: ToggleFeaturePayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    org = get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    flags = toggle_feature_flag(org_id, payload.feature_key, payload.is_enabled, actor_id=admin.id)
    write_platform_audit(
        action="feature.toggle",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=org_id,
        target_type="feature",
        target_id=payload.feature_key,
        message=f"{'Enabled' if payload.is_enabled else 'Disabled'} {payload.feature_key} for {org['name']}",
        ip_address=_client_ip(request),
        metadata={"feature_key": payload.feature_key, "is_enabled": payload.is_enabled},
    )
    return {"org_id": org_id, "flags": flags}


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/audit")
def api_list_audit(
    org_id: int | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    actor_name: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    query: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    admin: TokenData = Depends(require_platform_admin),
):
    return list_audit_logs(
        org_id=org_id,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        query=query,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )


@platform_router.get("/audit/export")
def api_export_audit(
    request: Request,
    org_id: int | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    actor_name: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    query: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    admin: TokenData = Depends(require_platform_admin),
):
    csv_content, row_count = export_audit_logs_csv(
        org_id=org_id,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        query=query,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
    )
    filename = f"platform-audit-{now_date()}.csv"
    write_platform_audit(
        action="audit.export",
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="audit",
        target_id="platform_audit_log",
        message=f"Exported {row_count} audit log entries",
        ip_address=_client_ip(request),
        metadata={
            "format": "csv",
            "filename": filename,
            "row_count": row_count,
            "filters": {
                "org_id": org_id,
                "actor_id": actor_id,
                "actor_name": actor_name,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "result": result,
                "query": query,
                "severity": severity,
                "from": from_date,
                "to": to_date,
            },
        },
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  INVITATIONS (public — no auth)
# ══════════════════════════════════════════════════════════════════════════════


invitation_router = APIRouter(tags=["Invitations"])


@invitation_router.get("/api/invitations/{token}/validate")
def api_validate_invitation(token: str):
    inv = validate_invitation(token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    return {
        "org_name": inv["org_name"],
        "org_type": inv["org_type"],
        "role": inv["role"],
        "email": inv["email"],
        "expires_at": inv["expires_at"],
    }


@invitation_router.post("/api/platform/invitations/accept", response_model=TokenResponse)
def api_accept_invitation(payload: AcceptInvitationPayload, request: Request, response: Response):
    try:
        user = accept_invitation_signup(payload.token, payload.full_name, payload.password)
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "already exists" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return issue_login_response(user, response, request)
