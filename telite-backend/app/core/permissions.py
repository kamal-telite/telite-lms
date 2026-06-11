"""Permission enforcement middleware."""

from __future__ import annotations

from typing import Callable
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.role_permission import RolePermission
from app.services.audit_service import AuditService

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
