"""Permission enforcement middleware."""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.engine import db_session
from app.models.role_permission import RolePermission
from app.services.audit_service import AuditService

logger = logging.getLogger("telite.permissions")

def resolve_permissions(
    role: str,
    is_platform_admin: bool,
    category_scope: str | None,
    org_id: int | None,
    db: Session | None = None
) -> list[str]:
    from app.core.rbac import ROLE_PERMISSIONS
    
    if is_platform_admin:
        return list(ROLE_PERMISSIONS.get("platform_admin", set()))
        
    active = set(ROLE_PERMISSIONS.get(role, set()))
    
    if db is not None and org_id is not None:
        try:
            overrides = db.query(RolePermission).filter(
                RolePermission.org_id == org_id,
                RolePermission.role == role
            ).all()
            for override in overrides:
                if override.enabled:
                    active.add(override.permission_key)
                else:
                    active.discard(override.permission_key)
        except Exception:
            logger.warning(
                "Failed to load org permission overrides for org_id=%s role=%s",
                org_id,
                role,
                exc_info=True,
            )

    return list(active)


def build_jwt_claims(user: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    role = user.get("role") or "learner"
    is_platform_admin = bool(user.get("is_platform_admin"))
    category_scope = user.get("category_scope")
    org_id = user.get("org_id") or user.get("organization_id")

    if db is not None:
        permissions = resolve_permissions(role, is_platform_admin, category_scope, org_id, db)
    else:
        try:
            from app.db.engine import get_db_session

            with get_db_session() as session:
                permissions = resolve_permissions(
                    role, is_platform_admin, category_scope, org_id, session
                )
        except Exception:
            logger.warning(
                "Falling back to static permissions for role=%s (no DB session)",
                role,
                exc_info=True,
            )
            permissions = resolve_permissions(
                role, is_platform_admin, category_scope, org_id, None
            )

    return {
        "sub": str(user.get("id")),
        "email": user.get("email"),
        "role": role,
        "name": user.get("full_name"),
        "org_id": org_id,
        "is_platform_admin": is_platform_admin,
        "permissions": permissions,
    }

def require_capability(permission_key: str) -> Callable:
    """
    Returns a FastAPI dependency that checks if the current user's role 
    has the specified capability in the active organization.
    """
    from app.api.auth import get_current_user, TokenData

    def dependency(
        db: Session = Depends(db_session),
        current_user: TokenData = Depends(get_current_user)
    ):
        # Super admin has unrestricted access
        if current_user.role == "super_admin":
            return current_user

        # Fetch the capability for the user's current active role and organization
        capability = db.query(RolePermission).filter(
            RolePermission.org_id == current_user.org_id,
            RolePermission.role == current_user.role,
            RolePermission.permission_key == permission_key,
            RolePermission.enabled
        ).first()

        if not capability:
            # Explicitly log permission denial
            AuditService.log(
                db=db,
                org_id=current_user.org_id,
                user_id=current_user.id,
                entity_type="system",
                entity_id=permission_key,
                action="permission.denied"
            )
            db.commit()
            
            raise HTTPException(
                status_code=403, 
                detail=f"You do not have the required capability: {permission_key}"
            )
            
        return current_user

    return dependency

def check_capability(db: Session, current_user: "TokenData", permission_key: str) -> bool:
    """
    Synchronously check capability when the required permission depends on the request payload.
    Raises 403 Forbidden if the user lacks the capability.
    """
    if current_user.role == "super_admin":
        return True

    capability = db.query(RolePermission).filter(
        RolePermission.org_id == current_user.org_id,
        RolePermission.role == current_user.role,
        RolePermission.permission_key == permission_key,
        RolePermission.enabled
    ).first()

    if not capability:
        AuditService.log(
            db=db,
            org_id=current_user.org_id,
            user_id=current_user.id,
            entity_type="system",
            entity_id=permission_key,
            action="permission.denied"
        )
        db.commit()
        raise HTTPException(
            status_code=403, 
            detail=f"You do not have the required capability: {permission_key}"
        )
        
    return True
