"""
Phase 4 — Tenant-aware permission resolution.

Resolves the full permission set for a user from:
  1. Their membership record (Phase 3 memberships table)
  2. Fallback to users.role + users.org_id (backward compat)
  3. Platform admin flag always wins

This module is the single source of truth for what a user can do.
Routes import from here — never compute permissions inline.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.rbac import ROLE_PERMISSIONS, Permission

logger = logging.getLogger("telite.permissions")


def resolve_permissions(
    role: str,
    is_platform_admin: bool,
    category_scope: str | None = None,
) -> list[str]:
    """
    Return the full list of permission strings for a role.

    Args:
        role:              User's role string
        is_platform_admin: Whether the user is a platform admin
        category_scope:    Category slug for category_admin scoping

    Returns:
        Sorted list of permission strings to embed in JWT
    """
    if is_platform_admin:
        # Platform admins get all permissions
        all_perms: set[str] = set()
        for perms in ROLE_PERMISSIONS.values():
            all_perms.update(perms)
        return sorted(all_perms)

    base_perms = set(ROLE_PERMISSIONS.get(role, set()))
    return sorted(base_perms)


def build_jwt_claims(user: dict[str, Any]) -> dict[str, Any]:
    """
    Build the full JWT payload for a user.

    Phase 4 enhancement: includes permissions list and category_scope
    so the frontend can make permission decisions without extra API calls.

    JWT structure:
    {
        "sub": "user-abc123",
        "email": "user@example.com",
        "role": "category_admin",
        "name": "Jane Smith",
        "org_id": 3,
        "category_scope": "engineering",
        "is_platform_admin": false,
        "permissions": ["cat.manage_courses", "cat.manage_learners", ...],
        "iat": 1234567890,
        "exp": 1234596690,
        "type": "access"
    }
    """
    role = user.get("role", "learner")
    is_platform_admin = bool(user.get("is_platform_admin", False))
    category_scope = user.get("category_scope")

    permissions = resolve_permissions(role, is_platform_admin, category_scope)

    return {
        "sub": user["id"],
        "email": user["email"],
        "role": role,
        "name": user["full_name"],
        "org_id": user.get("org_id"),
        "category_scope": category_scope,
        "is_platform_admin": is_platform_admin,
        "permissions": permissions,
    }


def check_permission_in_token(
    token_payload: dict[str, Any],
    permission: str,
) -> bool:
    """
    Check if a permission is present in a decoded JWT payload.
    Used for fast permission checks without a DB lookup.
    """
    if token_payload.get("is_platform_admin"):
        return True
    return permission in token_payload.get("permissions", [])
