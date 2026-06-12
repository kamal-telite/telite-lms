"""
Centralized RBAC (Role-Based Access Control) middleware for Telite LMS.

PHASE 2 SECURITY HARDENING:
- Single source of truth for all permission checks
- Tenant isolation enforced at middleware level
- Category scope validation
- Consistent error responses
- No scattered permission logic across routes
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.api.auth import (
    TokenData,
    get_current_user,
    ensure_org_access,
)

logger = logging.getLogger("telite.rbac")


# ── Permission constants ──────────────────────────────────────────────────────

class Permission:
    # Platform-level
    PLATFORM_MANAGE_ORGS = "platform.manage_orgs"
    PLATFORM_VIEW_ANALYTICS = "platform.view_analytics"
    PLATFORM_MANAGE_ADMINS = "platform.manage_admins"

    # Org-level
    ORG_MANAGE_USERS = "org.manage_users"
    ORG_MANAGE_COURSES = "org.manage_courses"
    ORG_MANAGE_CATEGORIES = "org.manage_categories"
    ORG_VIEW_ANALYTICS = "org.view_analytics"
    ORG_MANAGE_SETTINGS = "org.manage_settings"
    ORG_MANAGE_ENROLLMENTS = "org.manage_enrollments"

    ORG_MANAGE_PERMISSIONS = "org.manage_permissions"

    # Category-level
    CAT_MANAGE_COURSES = "cat.manage_courses"
    CAT_MANAGE_LEARNERS = "cat.manage_learners"
    CAT_VIEW_ANALYTICS = "cat.view_analytics"
    CAT_MANAGE_TASKS = "cat.manage_tasks"

    # Learner-level
    LEARNER_VIEW_COURSES = "learner.view_courses"
    LEARNER_ENROL = "learner.enrol"
    LEARNER_VIEW_PROGRESS = "learner.view_progress"

    # Authoring-level
    AUTHORING_MANAGE_BLOCKS = "authoring.manage_blocks"
    AUTHORING_MANAGE_SECTIONS = "authoring.manage_sections"
    AUTHORING_MANAGE_MODULES = "authoring.manage_modules"
    AUTHORING_MANAGE_MEDIA = "authoring.manage_media"
    AUTHORING_SUBMIT_REVIEW = "authoring.submit_review"
    AUTHORING_APPROVE_REJECT = "authoring.approve_reject"
    AUTHORING_PUBLISH = "authoring.publish"
    AUTHORING_ROLLBACK = "authoring.rollback"
    AUTHORING_VIEW_AUDIT_LOG = "authoring.view_audit_log"


# ── Role → Permission matrix ──────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "platform_admin": {
        Permission.PLATFORM_MANAGE_ORGS,
        Permission.PLATFORM_VIEW_ANALYTICS,
        Permission.PLATFORM_MANAGE_ADMINS,
        Permission.ORG_MANAGE_USERS,
        Permission.ORG_MANAGE_COURSES,
        Permission.ORG_MANAGE_CATEGORIES,
        Permission.ORG_VIEW_ANALYTICS,
        Permission.ORG_MANAGE_SETTINGS,
        Permission.ORG_MANAGE_ENROLLMENTS,
        Permission.CAT_MANAGE_COURSES,
        Permission.CAT_MANAGE_LEARNERS,
        Permission.CAT_VIEW_ANALYTICS,
        Permission.CAT_MANAGE_TASKS,
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
        Permission.AUTHORING_MANAGE_BLOCKS,
        Permission.AUTHORING_MANAGE_SECTIONS,
        Permission.AUTHORING_MANAGE_MODULES,
        Permission.AUTHORING_MANAGE_MEDIA,
        Permission.AUTHORING_SUBMIT_REVIEW,
        Permission.AUTHORING_APPROVE_REJECT,
        Permission.AUTHORING_PUBLISH,
        Permission.AUTHORING_ROLLBACK,
        Permission.AUTHORING_VIEW_AUDIT_LOG,
        Permission.ORG_MANAGE_PERMISSIONS,
    },
    "super_admin": {
        Permission.ORG_MANAGE_USERS,
        Permission.ORG_MANAGE_COURSES,
        Permission.ORG_MANAGE_CATEGORIES,
        Permission.ORG_VIEW_ANALYTICS,
        Permission.ORG_MANAGE_SETTINGS,
        Permission.ORG_MANAGE_ENROLLMENTS,
        Permission.CAT_MANAGE_COURSES,
        Permission.CAT_MANAGE_LEARNERS,
        Permission.CAT_VIEW_ANALYTICS,
        Permission.CAT_MANAGE_TASKS,
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
        Permission.AUTHORING_MANAGE_BLOCKS,
        Permission.AUTHORING_MANAGE_SECTIONS,
        Permission.AUTHORING_MANAGE_MODULES,
        Permission.AUTHORING_MANAGE_MEDIA,
        Permission.AUTHORING_SUBMIT_REVIEW,
        Permission.AUTHORING_APPROVE_REJECT,
        Permission.AUTHORING_PUBLISH,
        Permission.AUTHORING_ROLLBACK,
        Permission.AUTHORING_VIEW_AUDIT_LOG,
        Permission.ORG_MANAGE_PERMISSIONS,
    },
    "category_admin": {
        Permission.CAT_MANAGE_COURSES,
        Permission.CAT_MANAGE_LEARNERS,
        Permission.CAT_VIEW_ANALYTICS,
        Permission.CAT_MANAGE_TASKS,
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
        Permission.AUTHORING_MANAGE_BLOCKS,
        Permission.AUTHORING_MANAGE_SECTIONS,
        Permission.AUTHORING_MANAGE_MODULES,
        Permission.AUTHORING_MANAGE_MEDIA,
        Permission.AUTHORING_SUBMIT_REVIEW,
        Permission.AUTHORING_VIEW_AUDIT_LOG,
    },
    "author": {
        Permission.AUTHORING_MANAGE_BLOCKS,
        Permission.AUTHORING_MANAGE_SECTIONS,
        Permission.AUTHORING_MANAGE_MODULES,
        Permission.AUTHORING_MANAGE_MEDIA,
        Permission.AUTHORING_SUBMIT_REVIEW,
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
    },
    "reviewer": {
        Permission.AUTHORING_APPROVE_REJECT,
        Permission.AUTHORING_VIEW_AUDIT_LOG,
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
    },
    "learner": {
        Permission.LEARNER_VIEW_COURSES,
        Permission.LEARNER_ENROL,
        Permission.LEARNER_VIEW_PROGRESS,
    },
}


# ── Core permission check ─────────────────────────────────────────────────────

def has_permission(user: TokenData, permission: str) -> bool:
    """
    Check if a user has a specific permission.

    Platform admins always have all permissions. Phase 4 prefers signed JWT
    permission claims, with the matrix retained as a compatibility fallback.
    """
    if user.is_platform_admin:
        return True
    if permission in (user.permissions or []):
        return True

    role = user.role or "learner"
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory: require a specific permission.

    Usage:
        @router.get("/endpoint")
        def endpoint(user = Depends(require_permission(Permission.ORG_MANAGE_USERS))):
            ...
    """
    def _dependency(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        if not has_permission(current_user, permission):
            logger.warning(
                "Permission denied: user=%s role=%s required=%s",
                current_user.id,
                current_user.role,
                permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )
        return current_user

    return _dependency


# ── Org-scoped permission check ───────────────────────────────────────────────

def require_org_permission(permission: str) -> Callable:
    """
    FastAPI dependency factory: require a permission AND org-scoped access.

    The org_id must be passed as a query param or path param named 'org_id'.

    Usage:
        @router.get("/orgs/{org_id}/courses")
        def list_courses(
            org_id: int,
            user = Depends(require_org_permission(Permission.ORG_MANAGE_COURSES))
        ):
            ...
    """
    def _dependency(
        org_id: int,
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        # Check permission
        if not has_permission(current_user, permission):
            logger.warning(
                "Org permission denied: user=%s role=%s org=%s required=%s",
                current_user.id,
                current_user.role,
                org_id,
                permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )

        # Check org access
        ensure_org_access(current_user, org_id)

        return current_user

    return _dependency


# ── Category-scope check ──────────────────────────────────────────────────────

def validate_category_scope(user: TokenData, category_slug: str) -> None:
    """
    Validate that a category_admin is scoped to the requested category.

    Platform admins and super_admins bypass this check.
    """
    if user.is_platform_admin:
        return

    if user.role == "super_admin":
        return

    if user.role == "category_admin":
        if not user.category_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Category admin has no category scope assigned.",
            )
        if user.category_scope != category_slug and user.category_scope != "all":
            logger.warning(
                "Category scope mismatch: user=%s scope=%s requested=%s",
                user.id,
                user.category_scope,
                category_slug,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You are scoped to category '{user.category_scope}'.",
            )
        return

    # Learners cannot access admin category routes
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient role for category management.",
    )


def require_category_scope(permission: str) -> Callable:
    """
    FastAPI dependency factory: require permission + org access + category scope.

    Expects both 'org_id' and 'category_slug' as path/query params.

    Usage:
        @router.post("/orgs/{org_id}/categories/{category_slug}/courses")
        def create_course(
            org_id: int,
            category_slug: str,
            user = Depends(require_category_scope(Permission.CAT_MANAGE_COURSES))
        ):
            ...
    """
    def _dependency(
        org_id: int,
        category_slug: str,
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}",
            )

        ensure_org_access(current_user, org_id)
        validate_category_scope(current_user, category_slug)

        return current_user

    return _dependency


# ── Enrollment-specific guard ─────────────────────────────────────────────────

def validate_enrollment_access(
    current_user: TokenData,
    target_org_id: int,
    target_user_id: str | None = None,
) -> None:
    """
    Validate access for enrollment operations.

    - Platform admins: full access
    - Super admins: access within their org
    - Category admins: access within their org + category
    - Learners: can only access their own enrollments
    """
    ensure_org_access(current_user, target_org_id)

    if current_user.role == "learner" and target_user_id:
        if target_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Learners can only access their own enrollment data.",
            )


# ── Task-specific guard ───────────────────────────────────────────────────────

def validate_task_access(
    current_user: TokenData,
    task_org_id: int,
    task_category_slug: str | None = None,
) -> None:
    """
    Validate access for task operations.

    - Platform admins: full access
    - Super admins: access within their org
    - Category admins: access within their org + category scope
    - Learners: read-only access to their own tasks
    """
    ensure_org_access(current_user, task_org_id)

    if current_user.role == "category_admin" and task_category_slug:
        validate_category_scope(current_user, task_category_slug)


# ── Convenience dependency shortcuts ─────────────────────────────────────────

def require_any_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require platform_admin, super_admin, or category_admin role."""
    if current_user.role not in ("super_admin", "category_admin") and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_org_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require platform_admin or super_admin role."""
    if current_user.role != "super_admin" and not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation admin access required.",
        )
    return current_user
