"""Platform Admin API routes — /api/platform/*

All endpoints require is_platform_admin=1 on the authenticated user.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api.auth import TokenData, TokenResponse, issue_login_response, require_platform_admin
from app.services.store import (
    ADMIN_ROLES,
    SQL_LEARNER_ROLES,
    accept_invitation_signup,
    create_invitation,
    create_organization,
    fetch_user_by_id,
    get_all_org_feature_flags,
    get_conn,
    get_organization,
    list_audit_logs,
    list_moodle_tenants,
    list_organizations,
    list_pending_invitations,
    platform_analytics_overview,
    toggle_feature_flag,
    update_moodle_tenant_sync,
    update_organization,
    upsert_moodle_tenant,
    validate_invitation,
    write_platform_audit,
)

logger = logging.getLogger("telite.platform")

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


# ── Helper: get client IP ────────────────────────────────────────────────────


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
        org = create_organization(
            {
                "name": payload.name,
                "type": payload.type,
                "domain": payload.domain,
                "slug": payload.slug,
            },
            actor_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    invitation_sent = False

    # If moodle auto-setup requested, create moodle tenant placeholder
    if payload.moodle_setup == "auto":
        try:
            from app.integrations.moodle_bridge import moodle_create_category
            result = moodle_create_category(payload.name, parent_id=0)
            if result and result.get("id"):
                update_organization(org["id"], {"moodle_category_id": result["id"]})
                upsert_moodle_tenant(org["id"], result["id"])
        except Exception as exc:
            logger.warning("Moodle auto-setup failed for org %s: %s", org["id"], exc)
            upsert_moodle_tenant(org["id"], 0)
    elif payload.moodle_setup == "manual":
        upsert_moodle_tenant(org["id"], 0)

    # Send invitation to super admin
    if payload.super_admin_email:
        role = "super_admin"
        try:
            create_invitation(
                org_id=org["id"],
                email=payload.super_admin_email,
                role=role,
                invited_by=admin.id,
            )
            invitation_sent = True
        except ValueError as exc:
            logger.warning("Invitation creation failed: %s", exc)

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

    return {"org": org, "invitation_sent": invitation_sent}


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
    admin: TokenData = Depends(require_platform_admin),
):
    """List all admin-level users + pending invitations."""
    admin_roles = tuple(sorted(ADMIN_ROLES))
    placeholders = ",".join("?" for _ in admin_roles)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT u.id, u.full_name, u.email, u.role, u.org_id, u.status, u.last_login,
                   u.is_platform_admin, u.created_at,
                   o.name AS org_name, o.type AS org_type
            FROM users u
            LEFT JOIN organizations o ON o.id = u.org_id
            WHERE u.role IN ({placeholders})
            ORDER BY u.created_at DESC
            """,
            admin_roles,
        ).fetchall()
    admins = [dict(r) for r in rows]
    pending = list_pending_invitations()
    return {"admins": admins, "pending_invitations": pending}


@platform_router.post("/admins/invite", status_code=201)
def api_invite_admin(
    payload: InviteAdminPayload,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
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

    write_platform_audit(
        action="admin.invite",
        actor_id=admin.id,
        actor_name=admin.full_name,
        org_id=payload.org_id,
        target_type="user",
        target_id=payload.email,
        message=f"Invited {payload.email} as {payload.role} to {org['name']}",
        ip_address=_client_ip(request),
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
    with get_conn() as conn:
        new_active = 1 if payload.status == "active" else 0
        conn.execute("UPDATE users SET is_active = ?, status = ? WHERE id = ?", (new_active, payload.status, user_id))
        conn.commit()
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
    )
    return {"user_id": user_id, "status": payload.status}


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/analytics/overview")
def api_analytics_overview(
    admin: TokenData = Depends(require_platform_admin),
):
    return platform_analytics_overview()


@platform_router.get("/analytics/org/{org_id}")
def api_analytics_per_org(
    org_id: int,
    admin: TokenData = Depends(require_platform_admin),
):
    """Per-org analytics breakdown."""
    org = get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    with get_conn() as conn:
        users_by_role = [
            dict(r) for r in conn.execute(
                "SELECT role, COUNT(*) AS count FROM users WHERE org_id = ? GROUP BY role", (org_id,)
            ).fetchall()
        ]
        course_count = conn.execute(
            "SELECT COUNT(*) AS c FROM courses WHERE org_id = ?", (org_id,)
        ).fetchone()["c"]
        enrollment_count = conn.execute(
            "SELECT COUNT(*) AS c FROM enrollment_requests WHERE org_id = ?", (org_id,)
        ).fetchone()["c"]
        avg_pal = conn.execute(
            f"SELECT AVG(pal_score) AS avg FROM users WHERE org_id = ? AND role IN ({SQL_LEARNER_ROLES})",
            (org_id,),
        ).fetchone()["avg"]
        mt = conn.execute("SELECT * FROM moodle_tenants WHERE org_id = ?", (org_id,)).fetchone()
    return {
        "org_id": org_id,
        "org_name": org["name"],
        "users_by_role": users_by_role,
        "course_count": course_count,
        "enrollment_count": enrollment_count,
        "avg_pal_score": round(avg_pal, 1) if avg_pal else 0,
        "moodle_tenant": dict(mt) if mt else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MOODLE SYNC
# ══════════════════════════════════════════════════════════════════════════════


@platform_router.get("/moodle/tenants")
def api_moodle_tenants(
    admin: TokenData = Depends(require_platform_admin),
):
    return list_moodle_tenants()


@platform_router.post("/moodle/sync/{org_id}")
def api_moodle_sync_org(
    org_id: int,
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    org = get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org.get("status") != "active":
        raise HTTPException(status_code=400, detail="Organization is not active")

    # Get counts for this org
    with get_conn() as conn:
        users_lms = conn.execute("SELECT COUNT(*) AS c FROM users WHERE org_id = ?", (org_id,)).fetchone()["c"]
        courses = conn.execute("SELECT COUNT(*) AS c FROM courses WHERE org_id = ?", (org_id,)).fetchone()["c"]
        enrollments = conn.execute("SELECT COUNT(*) AS c FROM enrollment_requests WHERE org_id = ? AND status = 'approved'", (org_id,)).fetchone()["c"]

    try:
        # For now, just update the counts and mark as synced
        update_moodle_tenant_sync(
            org_id,
            status="synced",
            total_users_lms=users_lms,
            total_courses=courses,
            total_enrollments=enrollments,
        )
        write_platform_audit(
            action="moodle.sync",
            actor_id=admin.id,
            actor_name=admin.full_name,
            org_id=org_id,
            target_type="moodle",
            target_id=str(org_id),
            message=f"Moodle sync triggered for '{org['name']}'",
            ip_address=_client_ip(request),
        )
    except Exception as exc:
        update_moodle_tenant_sync(org_id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM moodle_tenants WHERE org_id = ?", (org_id,)).fetchone()
    return dict(row) if row else {}


@platform_router.post("/moodle/sync-all")
def api_moodle_sync_all(
    request: Request,
    admin: TokenData = Depends(require_platform_admin),
):
    """Trigger sync for all active orgs."""
    with get_conn() as conn:
        orgs = conn.execute(
            "SELECT o.id, o.name FROM organizations o JOIN moodle_tenants mt ON mt.org_id = o.id WHERE o.status = 'active'"
        ).fetchall()
    triggered = []
    for org in orgs:
        try:
            api_moodle_sync_org(org["id"], request, admin)
            triggered.append({"org_id": org["id"], "org_name": org["name"]})
        except Exception as exc:
            logger.warning("Sync failed for org %s: %s", org["id"], exc)
    return {"triggered": len(triggered), "orgs": triggered}


@platform_router.get("/moodle/sync-status")
def api_moodle_sync_status(
    admin: TokenData = Depends(require_platform_admin),
):
    return list_moodle_tenants()


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
    action: str | None = Query(default=None),
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
        action=action,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
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
def api_accept_invitation(payload: AcceptInvitationPayload):
    try:
        user = accept_invitation_signup(payload.token, payload.full_name, payload.password)
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "already exists" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return issue_login_response(user)
