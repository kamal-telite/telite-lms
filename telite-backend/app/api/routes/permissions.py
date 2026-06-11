from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from pydantic import BaseModel

from app.api.auth import get_current_user, TokenData
from app.core.rbac import require_org_admin
from app.db.engine import db_session
from app.models.role_permission import RolePermission
from app.core.rbac import ROLE_PERMISSIONS, Permission
from app.core.permissions import resolve_permissions

permissions_router = APIRouter(prefix="/authoring/permissions", tags=["Permissions Matrix"])

class PermissionUpdate(BaseModel):
    role: str
    updates: Dict[str, bool]

@permissions_router.get("", dependencies=[Depends(require_org_admin)])
def get_permission_matrix(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Returns the current permission matrix for the org.
    Calculates the exact set of enabled permissions by merging base defaults with DB overrides.
    """
    matrix = {}
    
    # We only expose authoring roles for matrix editing
    manageable_roles = ["category_admin", "author", "reviewer", "learner"]
    
    # Authoring capabilities we want to show
    authoring_keys = [
        Permission.AUTHORING_MANAGE_BLOCKS,
        Permission.AUTHORING_MANAGE_SECTIONS,
        Permission.AUTHORING_MANAGE_MODULES,
        Permission.AUTHORING_MANAGE_MEDIA,
        Permission.AUTHORING_SUBMIT_REVIEW,
        Permission.AUTHORING_APPROVE_REJECT,
        Permission.AUTHORING_PUBLISH,
        Permission.AUTHORING_ROLLBACK,
        Permission.AUTHORING_VIEW_AUDIT_LOG,
    ]
    
    for role in manageable_roles:
        # resolve_permissions handles base + overrides automatically
        active_perms = resolve_permissions(
            role=role, 
            is_platform_admin=False,
            category_scope=None,
            org_id=current_user.org_id, 
            db=db
        )
        
        role_map = {}
        for key in authoring_keys:
            role_map[key] = key in active_perms
            
        matrix[role] = role_map
        
    return {
        "roles": manageable_roles,
        "capabilities": authoring_keys,
        "matrix": matrix
    }

@permissions_router.put("", dependencies=[Depends(require_org_admin)])
def update_permission_matrix(
    updates: List[PermissionUpdate],
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Saves overrides to the role_permissions table.
    """
    for update in updates:
        role = update.role
        for key, is_enabled in update.updates.items():
            # Check if this matches the base default
            base_perms = ROLE_PERMISSIONS.get(role, set())
            is_default = key in base_perms
            
            existing = db.query(RolePermission).filter(
                RolePermission.org_id == current_user.org_id,
                RolePermission.role == role,
                RolePermission.permission_key == key
            ).first()
            
            if is_enabled == is_default:
                # If they are resetting to default, we can just delete the override
                if existing:
                    db.delete(existing)
            else:
                # Needs override
                if existing:
                    existing.enabled = is_enabled
                else:
                    new_override = RolePermission(
                        org_id=current_user.org_id,
                        role=role,
                        permission_key=key,
                        enabled=is_enabled
                    )
                    db.add(new_override)
                    
    db.commit()
    return {"success": True}
