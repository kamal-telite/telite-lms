"""Admin management endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import TokenData, ensure_org_access, require_admin, require_super_admin, resolve_org_scope
from app.db.engine import db_session
from app.repositories.user_repo import UserRepository
from app.repositories.org_repo import OrgRepository
from app.repositories.invite_repo import InviteRepository
from app.services.email import send_invitation_email
from app.services.user_provisioning import UserProvisioningService, ProvisioningError
from app.api.routes.management.schemas import AdminPayload, InviteAdminPayload
from app.api.routes.management.utils import (
    is_category_admin_role,
    org_id,
    SUPER_ADMIN_VISIBLE_ROLES,
    CATEGORY_ADMIN_VISIBLE_ROLES,
)

admins_router = APIRouter(tags=["Admin Management"])


@admins_router.get("/admins")
def get_admins(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Get all admins for an organization."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    user_repo = UserRepository(db)
    if is_category_admin_role(current_user.role):
        admins = [
            admin
            for admin in user_repo.list_admins_by_org(scoped_org_id, roles=["category_admin"])
            if admin.category_scope == current_user.category_scope
        ]
    else:
        admins = user_repo.list_admins_by_org(scoped_org_id, roles=["super_admin", "category_admin"])
    return {"admins": [a.to_dict() for a in admins]}


@admins_router.post("/admins")
def post_admin(
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Create or update an admin."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    try:
        existing = user_repo.get_by_email(body.email)
        if existing:
            if existing.org_id != scoped_org_id:
                raise HTTPException(status_code=403, detail="Email belongs to another organization")
            if existing.is_platform_admin or existing.role == "platform_admin":
                raise HTTPException(status_code=403, detail="Cannot modify platform administrator")
            if not existing.is_active or existing.status == "disabled":
                raise HTTPException(status_code=403, detail="Cannot modify an archived or inactive user")
            
            # Update existing
            old_role = existing.role
            update_kwargs = {
                "role": body.role,
                "full_name": body.full_name,
            }
            if body.category_scope:
                update_kwargs["category_scope"] = body.category_scope
                
            user_repo.update(existing, **update_kwargs)
            
            if body.password:
                user_repo.update_password(existing, body.password)
                
            if old_role != body.role:
                from app.services.notification_service import NotificationService
                notif_context = {
                    "new_role": body.role,
                    "user_id": existing.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                NotificationService(db).emit_event(
                    "user.role_changed",
                    scoped_org_id,
                    notif_context,
                    existing.id
                )
                
            db.commit()
            return existing.to_dict()
        else:
            if not body.username:
                raise HTTPException(status_code=400, detail="username is required")

            provision_svc = UserProvisioningService(db)
            try:
                inv = provision_svc.invite_admin(
                    email=body.email,
                    username=body.username,
                    full_name=body.full_name,
                    role=body.role,
                    org_id=scoped_org_id,
                    actor=actor,
                    category_scope=body.category_scope,
                )
                db.commit()
                return inv.to_dict()
            except ProvisioningError as pe:
                db.rollback()
                raise HTTPException(status_code=409, detail=str(pe))
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@admins_router.patch("/admins/{user_id}")
def patch_admin(
    user_id: str,
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Update an existing admin."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    existing = user_repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    ensure_org_access(current_user, existing.org_id)
    try:
        # Build update kwargs
        update_kwargs = {
            "full_name": body.full_name,
            "email": body.email,
            "role": body.role,
        }
        if body.category_scope is not None:
            update_kwargs["category_scope"] = body.category_scope
        if body.username:
            update_kwargs["username"] = body.username
            
        user_repo.update(existing, **update_kwargs)
        
        if body.password:
            user_repo.update_password(existing, body.password)
            
        db.commit()
        return existing.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@admins_router.post("/admins/invite", status_code=201)
def api_invite_admin(
    payload: InviteAdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Invite an admin via email."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    org_repo = OrgRepository(db)
    org = org_repo.get_by_id(scoped_org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    try:
        provision_svc = UserProvisioningService(db)
        invitation = provision_svc.invite_admin(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name or payload.email.split("@")[0],
            role=payload.role,
            org_id=scoped_org_id,
            actor=actor,
            category_scope=payload.category_scope,
        )
        invitation_id = invitation.id
        invitation_payload = invitation.to_dict()
        db.commit()
    except ProvisioningError as pe:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(pe))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
        
    delivered = send_invitation_email(
        to_email=invitation_payload["email"],
        org_name=org.name,
        org_domain=org.domain,
        role=invitation_payload["role"],
        token=invitation_payload["token"],
        expires_at=str(invitation_payload["expires_at"]),
    )
    
    try:
        invite_repo = InviteRepository(db)
        invite_repo.record_delivery(invitation_id, delivered=delivered)
        db.commit()
        invitation_payload["delivery_status"] = "delivered" if delivered else "failed"
    except:
        db.rollback()
    
    return {"message": "Invitation sent successfully", "invitation": invitation_payload}


@admins_router.delete("/admins/{user_id}")
def delete_admin(
    user_id: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Deactivate an admin (soft delete)."""
    user_repo = UserRepository(db)
    existing = user_repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    ensure_org_access(current_user, existing.org_id)
    try:
        existing.is_active = False
        existing.status = "disabled"
        db.commit()
        return {"status": "success"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
