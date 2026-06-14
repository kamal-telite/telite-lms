"""Permission enforcement middleware."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user
from app.core.rbac import ROLE_PERMISSIONS
from app.db.engine import db_session
from app.models.role_permission import RolePermission
from app.services.audit_service import AuditService


def resolve_permissions(
    role: str,
    is_platform_admin: bool = False,
    category_scope: str | None = None,
    org_id: int | None = None,
    db: Session | None = None,
) -> list[str]:
    """Merge role defaults with per-organization permission overrides."""
    _ = category_scope

    if is_platform_admin:
        return sorted(ROLE_PERMISSIONS.get("platform_admin", set()))

    effective_role = role or "learner"
    permissions = set(ROLE_PERMISSIONS.get(effective_role, set()))

    if db is not None and org_id is not None:
        overrides = (
            db.query(RolePermission)
            .filter(
                RolePermission.org_id == org_id,
                RolePermission.role == effective_role,
            )
            .all()
        )
        for override in overrides:
            if override.enabled:
                permissions.add(override.permission_key)
            else:
                permissions.discard(override.permission_key)

    return sorted(permissions)


def build_jwt_claims(user: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    """Build JWT claims, including resolved permissions, for an authenticated user."""
    role = user.get("role") or "learner"
    is_platform_admin = bool(user.get("is_platform_admin", False))
    category_scope = user.get("category_scope")
    org_id = user.get("org_id") or user.get("organization_id")

    permissions = resolve_permissions(
        role,
        is_platform_admin,
        category_scope,
        org_id,
        db,
    )

    return {
        "sub": user["id"],
        "email": user["email"],
        "role": role,
        "name": user["full_name"],
        "org_id": org_id,
        "category_scope": category_scope,
        "is_platform_admin": is_platform_admin,
        "permissions": permissions,
    }


def require_capability(permission_key: str) -> Callable:
    """
    Returns a FastAPI dependency that checks if the current user's role 
    has the specified capability in the active organization.
    """
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
            RolePermission.enabled == True
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

def check_capability(db: Session, current_user: TokenData, permission_key: str) -> bool:
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
        RolePermission.enabled == True
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
