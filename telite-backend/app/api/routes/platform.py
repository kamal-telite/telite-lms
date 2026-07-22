from __future__ import annotations

import hashlib
import logging
import os
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.engine import platform_db_session

from app.api.auth import TokenData, TokenResponse, issue_login_response, require_platform_admin

from app.services.auth_rate_limiter import is_limited, record_attempt
from app.services.email import send_invitation_email, send_password_reset_email

from app.repositories.org_repo import OrgRepository
from app.repositories.user_repo import UserRepository
from app.repositories.invite_repo import InviteRepository
from app.repositories.audit_repo import AuditRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.services.user_provisioning import UserProvisioningService, ProvisioningError
from app.core.identifier_masking import mask_identifier

logger = logging.getLogger("telite.platform")

PLATFORM_ADMIN_INVITE_LIMIT = int(os.getenv("TELITE_PLATFORM_ADMIN_INVITE_LIMIT", "5"))
PLATFORM_ADMIN_INVITE_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_ADMIN_INVITE_WINDOW_SECONDS", "600"))
PLATFORM_PASSWORD_RESET_LIMIT = int(os.getenv("TELITE_PLATFORM_PASSWORD_RESET_LIMIT", "5"))
PLATFORM_PASSWORD_RESET_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_PASSWORD_RESET_WINDOW_SECONDS", "900"))
PLATFORM_ANALYTICS_ALERT_LIMIT = int(os.getenv("TELITE_PLATFORM_ANALYTICS_ALERT_LIMIT", "10"))
PLATFORM_ANALYTICS_ALERT_WINDOW_SECONDS = int(os.getenv("TELITE_PLATFORM_ANALYTICS_ALERT_WINDOW_SECONDS", "600"))

platform_router = APIRouter(prefix="/api/platform", tags=["Platform Admin"])
invitation_router = APIRouter(tags=["Invitations"])

# ── Pydantic models ──

class CreateOrgPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: str = Field(..., pattern=r"^(college|company)$")
    domain: str = Field(..., min_length=3)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$")
    super_admin_email: str | None = None

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

# ── Helper: get client IP ──

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
    db: Session = Depends(platform_db_session),
):
    repo = OrgRepository(db)
    org_type_filter = type if type != "all" else None
    status_filter = status if status != "all" else None
    
    offset = (page - 1) * limit
    orgs = repo.list_all(status=status_filter, org_type=org_type_filter, search=search, limit=limit, offset=offset)
    
    return {
        "organizations": [org.to_dict() for org in orgs],
        "total": len(orgs), # Just approximate
        "page": page,
        "limit": limit
    }

@platform_router.post("/organizations", status_code=201)
def api_create_organization(
    payload: CreateOrgPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    repo = OrgRepository(db)
    
    try:
        org = repo.create_org(
            name=payload.name,
            org_type=payload.type,
            domain=payload.domain,
            slug=payload.slug,
            created_by=admin.id
        )
        db.flush()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
        
    invitation_sent = False
    invitation = None
    
    if payload.super_admin_email:
        invite_repo = InviteRepository(db)
        invitation_obj = invite_repo.create_invitation(
            org_id=org.id,
            email=payload.super_admin_email,
            role="super_admin",
            invited_by=admin.id
        )
        db.flush()
        invitation = invitation_obj.to_dict()
        
        delivered = send_invitation_email(
            to_email=invitation["email"],
            org_name=org.name,
            org_domain=org.domain,
            role=invitation["role"],
            token=invitation["token"],
            expires_at=invitation["expires_at"],
        )
        
        invite_repo.record_delivery(invitation_obj.id, delivered=delivered)
        db.flush()
        
        invitation["delivery_status"] = "delivered" if delivered else "failed"
        invitation_sent = delivered

    audit = AuditRepository(db)
    audit.write(
        org_id=org.id,
        action="organization.created",
        actor_user_id=admin.id,
        actor_name=admin.full_name,
        target_type="org",
        target_id=str(org.id),
        message=f"Created organization '{payload.name}' ({payload.type})",
        ip_address=_client_ip(request),
        metadata={"domain": payload.domain},
    )
    db.flush()

    return {
        "org": org.to_dict(),
        "invitation_sent": invitation_sent,
    }

@platform_router.get("/organizations/{org_id}")
def api_get_organization(
    org_id: int,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    org = OrgRepository(db).get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org.to_dict()

@platform_router.patch("/organizations/{org_id}")
def api_update_organization(
    org_id: int,
    payload: UpdateOrgPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    repo = OrgRepository(db)
    org = repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
        
    try:
        updated = repo.update_org(org, **updates)
        db.flush()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))

    AuditRepository(db).log_action(
        org_id=org_id,
        action="org.update",
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="org",
        target_id=str(org_id),
        message=f"Updated organization '{org.name}'",
        ip_address=_client_ip(request),
        metadata=updates,
    )
    db.flush()
    return updated.to_dict()

@platform_router.patch("/organizations/{org_id}/status")
def api_update_org_status(
    org_id: int,
    payload: UpdateStatusPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    repo = OrgRepository(db)
    org = repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    if payload.status == "suspended":
        repo.suspend_org(org_id)
    else:
        repo.activate_org(org_id)
    db.flush()
    
    action = "org.suspend" if payload.status == "suspended" else "org.activate"
    AuditRepository(db).log_action(
        org_id=org_id,
        action=action,
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="org",
        target_id=str(org_id),
        message=f"Set organization '{org.name}' to {payload.status}",
        severity="WARN" if payload.status == "suspended" else "INFO",
        ip_address=_client_ip(request),
    )
    db.flush()
    return org.to_dict()

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
    db: Session = Depends(platform_db_session),
):
    user_repo = UserRepository(db)
    offset = (page - 1) * limit
    
    is_active = True if status == "active" else (False if status == "suspended" else None)
    role_filter = role if role != "all" else None
    admin_roles = [role_filter] if role_filter else ["super_admin", "category_admin", "platform_admin"]

    from sqlalchemy import select, or_
    from app.models.user import User
    
    stmt = select(User).where(User.role.in_(admin_roles))
    if org_id is not None:
        stmt = stmt.where(User.org_id == org_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if query:
        search_filter = f"%{query}%"
        stmt = stmt.where(or_(
            User.full_name.ilike(search_filter),
            User.email.ilike(search_filter),
            User.username.ilike(search_filter)
        ))
        
    total = len(db.scalars(stmt).all())
    stmt = stmt.limit(limit).offset(offset)
    users = db.scalars(stmt).all()

    return {
        "admins": [u.to_dict() for u in users],
        "total": total
    }

@platform_router.get("/admins/invitations")
def api_list_admin_invitations(
    org_id: int | None = Query(default=None),
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    invite_repo = InviteRepository(db)
    org_repo = OrgRepository(db)
    invitations = []
    for invitation in invite_repo.list_pending(org_id=org_id):
        item = invitation.to_dict()
        org = org_repo.get_by_id(invitation.org_id)
        item["org_name"] = org.name if org else None
        item["org_type"] = org.type if org else None
        invitations.append(item)

    return {
        "pending_invitations": invitations,
        "total": len(invitations),
    }

@platform_router.post("/admins/invite", status_code=201)
def api_invite_admin(
    payload: InviteAdminPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-admin-invite",
        subject=f"{admin.id}:{payload.org_id}:{_client_ip(request)}",
        limit=PLATFORM_ADMIN_INVITE_LIMIT,
        window_seconds=PLATFORM_ADMIN_INVITE_WINDOW_SECONDS,
    )
    org = OrgRepository(db).get_by_id(payload.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    try:
        invite_repo = InviteRepository(db)
        invitation_obj = invite_repo.create_invitation(
            org_id=payload.org_id,
            email=payload.email,
            role=payload.role,
            invited_by=admin.id,
        )
        db.flush()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
        
    delivered = send_invitation_email(
        to_email=invitation_obj.email,
        org_name=org.name,
        org_domain=org.domain,
        role=invitation_obj.role,
        token=invitation_obj.token,
        expires_at=invitation_obj.expires_at.isoformat(),
    )
    
    invite_repo.record_delivery(invitation_obj.id, delivered=delivered)
    db.flush()

    AuditRepository(db).write(
        org_id=payload.org_id,
        action="admin.invite",
        actor_user_id=admin.id,
        actor_name=admin.full_name,
        target_type="user",
        target_id=payload.email,
        message=f"Invited {mask_identifier(payload.email)} as {payload.role} to {org.name}",
        ip_address=_client_ip(request),
        metadata={"delivery_status": "delivered" if delivered else "failed"},
    )
    db.flush()
    
    return {"invitation": invitation_obj.to_dict()}

@platform_router.post("/admins/invitations/{invitation_id}/resend")
def api_resend_admin_invitation(
    invitation_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    invite_repo = InviteRepository(db)
    invitation = invite_repo.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
        
    invite_repo.record_resend(invitation.id)
    db.flush()
    
    org = OrgRepository(db).get_by_id(invitation.org_id)

    delivered = send_invitation_email(
        to_email=invitation.email,
        org_name=org.name if org else "Platform",
        org_domain=org.domain if org else "telite.in",
        role=invitation.role,
        token=invitation.token,
        expires_at=str(invitation.expires_at),
    )
    
    invite_repo.record_delivery(invitation.id, delivered=delivered)
    db.flush()

    AuditRepository(db).write(
        org_id=invitation.org_id,
        action="invite.resend",
        actor_user_id=admin.id,
        actor_name=admin.full_name,
        target_type="invitation",
        target_id=str(invitation_id),
        message=f"Resent invitation to {mask_identifier(invitation.email)}",
        ip_address=_client_ip(request),
        metadata={"delivery_status": "delivered" if delivered else "failed"},
    )
    db.flush()
    return {"invitation": invitation.to_dict()}

@platform_router.delete("/admins/invitations/{invitation_id}")
def api_revoke_admin_invitation(
    invitation_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    invite_repo = InviteRepository(db)
    invitation = invite_repo.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found.")
        
    invite_repo.revoke_invitation(invitation.id, revoked_by=admin.id)
    db.flush()

    AuditRepository(db).write(
        org_id=invitation.org_id,
        action="invite.revoke",
        actor_user_id=admin.id,
        actor_name=admin.full_name,
        target_type="invitation",
        target_id=str(invitation_id),
        message=f"Revoked invitation for {invitation.email}",
        ip_address=_client_ip(request),
        severity="WARN",
        metadata={"email": invitation.email},
    )
    db.flush()
    return {"invitation": invitation.to_dict()}

@platform_router.patch("/admins/{user_id}/status")
def api_update_admin_status(
    user_id: str,
    payload: UpdateAdminStatusPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_repo.set_active(user, is_active=(payload.status == "active"))
    db.flush()
    
    action = "admin.suspend" if payload.status == "suspended" else "admin.activate"
    AuditRepository(db).log_action(
        org_id=user.org_id,
        action=action,
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="user",
        target_id=user_id,
        message=f"Set admin '{user.full_name}' to {payload.status}",
        severity="WARN" if payload.status == "suspended" else "INFO",
        ip_address=_client_ip(request),
    )
    db.flush()
    return {"user_id": user_id, "status": payload.status}

@platform_router.delete("/admins/{user_id}")
def api_delete_admin(
    user_id: str,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin.id:
        raise HTTPException(status_code=409, detail="You cannot delete your own platform admin account")
    if user.is_platform_admin:
        raise HTTPException(status_code=409, detail="Platform admin accounts cannot be deleted from this endpoint")
        
    user_repo.set_active(user, is_active=False)
    db.flush()

    AuditRepository(db).log_action(
        org_id=user.org_id,
        action="admin.delete",
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="user",
        target_id=user_id,
        message=f"Deleted admin '{user.full_name}'",
        severity="WARN",
        ip_address=_client_ip(request),
    )
    db.flush()
    return {"user": user.to_dict(), "deleted": True}

@platform_router.post("/admins/{user_id}/reset-password")
def api_trigger_admin_password_reset(
    user_id: str,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    _enforce_endpoint_rate_limit(
        namespace="platform-admin-password-reset",
        subject=f"{admin.id}:{user_id}:{_client_ip(request)}",
        limit=PLATFORM_PASSWORD_RESET_LIMIT,
        window_seconds=PLATFORM_PASSWORD_RESET_WINDOW_SECONDS,
    )
    
    # Normally we would create a reset token using AuthRepo, this is a mock implementation
    # since we are dropping legacy SQL repo.
    return {
        "status": "reset_requested",
        "user_id": user_id
    }

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@platform_router.get("/analytics/overview")
def api_analytics_overview(
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    repo = AnalyticsRepository(db)
    return repo.get_platform_overview()

@platform_router.get("/analytics/export")
def api_export_analytics(
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    repo = AnalyticsRepository(db)
    csv_content = repo.export_platform_overview_csv()
    filename = f"platform-analytics-{datetime.now().date().isoformat()}.csv"
    
    AuditRepository(db).log_action(
        org_id=None,
        action="analytics.export",
        actor_id=admin.id,
        actor_name=admin.full_name,
        target_type="analytics",
        target_id="platform_overview",
        message="Exported platform analytics overview",
        ip_address=_client_ip(request),
        metadata={"format": "csv", "filename": filename},
    )
    db.flush()
    
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
    db: Session = Depends(platform_db_session),
):
    repo = AnalyticsRepository(db)
    return repo.get_platform_org_analytics_detail(org_id, days=days)

@platform_router.post("/analytics/alerts", status_code=201)
def api_create_analytics_alert(
    payload: CreateAnalyticsAlertPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    return {"rule": {"id": 1, "metric": payload.metric, "threshold": payload.threshold, "channel": payload.channel}}

# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE FLAGS
# ══════════════════════════════════════════════════════════════════════════════

@platform_router.get("/features")
def api_list_features(
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    return {"features": []}

@platform_router.patch("/features/{org_id}")
def api_toggle_feature(
    org_id: int,
    payload: ToggleFeaturePayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
    db: Session = Depends(platform_db_session),
):
    return {"org_id": org_id, "flags": []}

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
    db: Session = Depends(platform_db_session),
):
    repo = AuditRepository(db)
    offset = (page - 1) * limit
    logs = repo.list_audit_logs(
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        limit=limit,
        offset=offset
    )
    return {"logs": [log.to_dict() for log in logs], "total": len(logs)}

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
    db: Session = Depends(platform_db_session),
):
    csv_content = "id,action,actor\n1,test,admin"
    filename = f"platform-audit-{datetime.now().date().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# ══════════════════════════════════════════════════════════════════════════════
#  INVITATIONS (public — no auth)
# ══════════════════════════════════════════════════════════════════════════════

@invitation_router.get("/api/invitations/{token}/validate")
def api_validate_invitation(token: str, db: Session = Depends(platform_db_session)):
    repo = InviteRepository(db)
    inv = repo.get_by_token(token)
    if not inv or inv.is_expired():
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    
    org = OrgRepository(db).get_by_id(inv.org_id)
    return {
        "org_name": org.name if org else "Platform",
        "org_type": org.type if org else "company",
        "role": inv.role,
        "email": inv.email,
        "expires_at": inv.expires_at,
    }

@invitation_router.post("/api/platform/invitations/accept", response_model=TokenResponse)
def api_accept_invitation(payload: AcceptInvitationPayload, request: Request, response: Response, db: Session = Depends(platform_db_session)):
    try:
        provisioning_service = UserProvisioningService(db)
        user = provisioning_service.accept_invitation(payload.token, payload.password, payload.full_name)
    except ProvisioningError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return issue_login_response(db, user, response, request)
