"""Management API utility functions."""

from typing import Any


def is_admin_role(role: str) -> bool:
    """Check if the role is an admin role."""
    return role in ("super_admin", "category_admin")


def is_category_admin_role(role: str) -> bool:
    """Check if the role is a category admin."""
    return role == "category_admin"


def is_learner_role(role: str) -> bool:
    """Check if the role is a learner."""
    return role == "learner"


def is_tenant_super_admin_role(role: str) -> bool:
    """Check if the role is a tenant super admin."""
    return role == "super_admin"


SUPER_ADMIN_VISIBLE_ROLES = ("super_admin", "category_admin", "instructor", "learner")
CATEGORY_ADMIN_VISIBLE_ROLES = ("category_admin", "instructor", "learner")


def org_id(record: Any) -> int | None:
    """Extract org_id from a record (dict or object)."""
    if not record:
        return None
    if isinstance(record, dict):
        return record.get("org_id") or record.get("organization_id")
    return getattr(record, "org_id", getattr(record, "organization_id", None))


def can_access_user(viewer: Any, target: Any) -> bool:
    """Check if a viewer can access a target user."""
    viewer_is_platform_admin = getattr(viewer, "is_platform_admin", False)
    if viewer_is_platform_admin:
        return True
    
    viewer_org_id = getattr(viewer, "org_id", None)
    target_org_id = org_id(target)
    if viewer_org_id is None or target_org_id != viewer_org_id:
        return False
    
    viewer_role = getattr(viewer, "role", None)
    if is_tenant_super_admin_role(viewer_role):
        target_is_platform_admin = getattr(target, "is_platform_admin", False)
        target_role = getattr(target, "role", None)
        return not target_is_platform_admin and target_role != "platform_admin"
    
    if is_category_admin_role(viewer_role):
        return (
            getattr(target, "category_scope", None) == getattr(viewer, "category_scope", None)
            and getattr(target, "role", None) in CATEGORY_ADMIN_VISIBLE_ROLES
            and not getattr(target, "is_platform_admin", False)
        )
    
    return getattr(viewer, "id", None) == getattr(target, "id", None)
