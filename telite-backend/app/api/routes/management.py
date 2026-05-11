from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, require_super_admin, resolve_org_scope
from app.integrations.moodle_bridge import (
    moodle_create_category,
    moodle_create_course,
    moodle_delete_category,
    moodle_delete_courses,
    moodle_mode,
    moodle_suspend_user,
)
from app.integrations.moodle_reports import build_moodle_settings_snapshot, build_moodle_user_directory
from app.services.store import (
    archive_category,
    archive_course,
    build_launch_payload,
    create_category,
    create_or_update_admin,
    create_or_update_course,
    ensure_category_access,
    fetch_user_by_id,
    get_category,
    get_course,
    get_system_settings,
    get_user_activity,
    is_admin_role,
    is_category_admin_role,
    is_learner_role,
    is_tenant_super_admin_role,
    list_admins,
    list_categories,
    list_courses,
    list_notifications,
    list_users,
    remove_admin,
    set_user_active,
    soft_delete_user,
    update_category,
    update_category_moodle_id,
    update_user_role,
)

logger = logging.getLogger("telite.management")


management_router = APIRouter(tags=["Management"])


def _org_id(record: dict[str, Any] | None) -> int | None:
    if not record:
        return None
    return record.get("org_id") or record.get("organization_id")


class CategoryPayload(BaseModel):
    name: str
    slug: str
    description: str | None = ""
    admin_user_id: str | None = None
    planned_courses: int = Field(default=0, ge=0)
    status: str = "active"
    accent_color: str | None = None
    org_type: str = "college"
    organization_id: int | None = None


class AdminPayload(BaseModel):
    full_name: str
    email: str
    role: str
    category_scope: str | None = None
    password: str | None = None
    username: str | None = None


class CoursePayload(BaseModel):
    name: str
    slug: str | None = None
    description: str
    tier: str
    status: str = "draft"
    module_count: int = Field(default=4, ge=0)
    modules: list[str] = Field(default_factory=list)
    lessons_count: int = Field(default=8, ge=0)
    hours: float = Field(default=12, ge=0)
    prerequisite_course_id: str | None = None
    moodle_course_id: int | None = None


class UserRolePayload(BaseModel):
    role: str
    category_scope: str | None = None


class UserActivePayload(BaseModel):
    is_active: bool


@management_router.get("/categories")
def get_categories(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"categories": list_categories(include_archived=True, org_id=scoped_org_id)}


@management_router.post("/categories")
def post_category(
    body: CategoryPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    payload = body.model_dump()
    scoped_org_id = payload.get("organization_id") or resolve_org_scope(current_user, org_id)
    payload["organization_id"] = scoped_org_id
    payload["org_id"] = scoped_org_id
    existing = next(
        (
            category
            for category in list_categories(include_archived=True, org_id=scoped_org_id)
            if category["slug"] == payload["slug"]
        ),
        None,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Category slug already exists.")

    try:
        # Step 1: Sync to Moodle first
        logger.info("Creating category in Moodle: name=%s slug=%s", payload["name"], payload["slug"])
        moodle_sync = moodle_create_category(
            payload["name"],
            slug=payload["slug"],
            description=payload.get("description", "") or "",
        )
        if not moodle_sync.get("success"):
            logger.error("Moodle category sync failed: %s", moodle_sync.get("error"))
            raise HTTPException(
                status_code=502,
                detail=f"Unable to create the category in Moodle: {moodle_sync.get('error', 'Unknown Moodle error')}",
            )

        # Step 2: Write to local DB
        created = create_category(payload, actor)

        # Step 3: Store the Moodle category ID in local DB
        moodle_category_id = moodle_sync.get("category_id")
        if moodle_category_id and created:
            update_category_moodle_id(created["id"], int(moodle_category_id))
            logger.info(
                "Category synced: local_id=%s moodle_id=%s already_existed=%s",
                created["id"],
                moodle_category_id,
                moodle_sync.get("already_existed", False),
            )

        return {**created, "moodle_sync": moodle_sync}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.patch("/categories/{category_id}")
def patch_category(
    category_id: str,
    body: CategoryPayload,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    existing = get_category(category_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    ensure_org_access(current_user, _org_id(existing))
    try:
        return update_category(category_id, body.model_dump(exclude_unset=True), actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        # Fetch category first to check Moodle ID
        from app.services.store import get_category
        category_data = get_category(category_id)
        if not category_data:
            raise ValueError("Category not found.")
        ensure_org_access(current_user, _org_id(category_data))

        # Try deleting in Moodle first
        if category_data.get("moodle_category_id"):
            moodle_res = moodle_delete_category(category_data["moodle_category_id"])
            if not moodle_res.get("success"):
                raise ValueError(f"Failed to sync deletion with Moodle: {moodle_res.get('error')}")

        # If Moodle succeeds (or not linked), archive locally
        category = archive_category(category_id, actor)
        return category
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.get("/admins")
def get_admins(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"admins": list_admins(scoped_org_id)}


@management_router.post("/admins")
def post_admin(
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        payload = body.model_dump()
        scoped_org_id = resolve_org_scope(current_user, org_id)
        payload["organization_id"] = scoped_org_id
        payload["org_id"] = scoped_org_id
        return create_or_update_admin(payload, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.patch("/admins/{user_id}")
def patch_admin(
    user_id: str,
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        existing = fetch_user_by_id(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Admin not found")
        ensure_org_access(current_user, _org_id(existing))
        payload = body.model_dump()
        scoped_org_id = _org_id(existing) or resolve_org_scope(current_user, org_id)
        payload["organization_id"] = scoped_org_id
        payload["org_id"] = scoped_org_id
        return create_or_update_admin(payload, actor, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.delete("/admins/{user_id}")
def delete_admin(
    user_id: str,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        existing = fetch_user_by_id(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Admin not found")
        ensure_org_access(current_user, _org_id(existing))
        user = remove_admin(user_id, actor)
        if user.get("moodle_user_id"):
            moodle_suspend_user(user["moodle_user_id"])
        return user
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@management_router.get("/categories/{category_slug}/courses")
def get_category_courses(
    category_slug: str,
    current_user: TokenData = Depends(get_current_user),
):
    category = get_category(category_slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    ensure_org_access(current_user, _org_id(category))
    viewer = fetch_user_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    if is_learner_role(viewer["role"]):
        if viewer["category_scope"] != category_slug:
            raise HTTPException(status_code=403, detail="You do not have access to this category.")
    else:
        try:
            ensure_category_access(viewer, category_slug)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"courses": list_courses(category_slug, include_archived=True, org_id=_org_id(category))}


@management_router.post("/categories/{category_slug}/courses")
def post_course(
    category_slug: str,
    body: CoursePayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, category_slug)
        
        # Step 1: Fetch local category to get Moodle category ID
        category_data = get_category(category_slug)
        if not category_data:
            raise ValueError("Category not found.")
            
        moodle_category_id = category_data.get("moodle_category_id")
        moodle_sync = None
        
        # Step 2: Create in Moodle
        if moodle_category_id:
            logger.info("Creating course in Moodle: name=%s category_id=%s", body.name, moodle_category_id)
            moodle_sync = moodle_create_course(body.name, moodle_category_id)
            if not moodle_sync.get("success"):
                logger.error("Moodle course sync failed: %s", moodle_sync.get("error"))
                raise HTTPException(
                    status_code=502,
                    detail=f"Unable to create the course in Moodle: {moodle_sync.get('error', 'Unknown error')}"
                )
            body.moodle_course_id = moodle_sync.get("course_id")
            
        # Step 3: Write to local DB
        created_course = create_or_update_course(category_slug, body.model_dump(), actor)
        return {**created_course, "moodle_sync": moodle_sync}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.patch("/categories/{category_slug}/courses/{course_id}")
def patch_course(
    category_slug: str,
    course_id: str,
    body: CoursePayload,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, category_slug)
        return create_or_update_course(category_slug, body.model_dump(), actor, course_id=course_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@management_router.delete("/categories/{category_slug}/courses/{course_id}")
def delete_course(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    try:
        ensure_category_access(actor, category_slug)
        course = archive_course(course_id, actor)
        if course.get("moodle_course_id"):
            moodle_delete_courses([course["moodle_course_id"]])
        return course
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@management_router.get("/courses/{course_id}/launch")
def launch_course(
    course_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    ensure_org_access(current_user, _org_id(course))
    viewer = fetch_user_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    if is_learner_role(viewer["role"]) and viewer["category_scope"] != course["category_slug"]:
        raise HTTPException(status_code=403, detail="You are not enrolled in this category.")
    if is_category_admin_role(viewer["role"]) and viewer["category_scope"] != course["category_slug"]:
        raise HTTPException(status_code=403, detail="You do not manage this category.")
    return build_launch_payload(course_id, viewer)


@management_router.get("/users")
def get_users(
    role: str | None = Query(default=None),
    category_slug: str | None = Query(default=None),
    query: str | None = Query(default=None),
    enrollment_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    org_id: int | None = Query(default=None, alias="orgId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: TokenData = Depends(require_admin),
):
    if source == "moodle" and is_tenant_super_admin_role(current_user.role) and moodle_mode() == "live":
        return build_moodle_user_directory(role=role, query=query, page=page, page_size=page_size)

    scoped_org_id = resolve_org_scope(current_user, org_id)
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
        if role and is_tenant_super_admin_role(role):
            raise HTTPException(status_code=403, detail="Category admins cannot view super admin users.")
    offset = (page - 1) * page_size
    return list_users(
        role=role,
        category_slug=category_slug,
        query=query,
        enrollment_type=enrollment_type,
        org_id=scoped_org_id,
        limit=page_size,
        offset=offset,
        include_inactive=is_tenant_super_admin_role(current_user.role),
    )


def _can_access_user(viewer: TokenData, target: dict[str, Any]) -> bool:
    if viewer.is_platform_admin:
        return True
    if viewer.org_id is None or _org_id(target) != viewer.org_id:
        return False
    if is_tenant_super_admin_role(viewer.role):
        return True
    if is_category_admin_role(viewer.role):
        return target["category_scope"] == viewer.category_scope or is_admin_role(target["role"])
    return viewer.id == target["id"]


@management_router.get("/users/{user_id}")
def get_user(user_id: str, current_user: TokenData = Depends(get_current_user)):
    user = fetch_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_access_user(current_user, user):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
    return user


@management_router.patch("/users/{user_id}/role")
def patch_user_role(
    user_id: str,
    body: UserRolePayload,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    target = fetch_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, _org_id(target))
    try:
        return update_user_role(user_id, body.role, actor, category_scope=body.category_scope)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@management_router.patch("/users/{user_id}/activate")
def patch_user_active(
    user_id: str,
    body: UserActivePayload,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    target = fetch_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, _org_id(target))
    try:
        return set_user_active(user_id, body.is_active, actor)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@management_router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: TokenData = Depends(require_super_admin),
):
    actor = fetch_user_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    target = fetch_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, _org_id(target))
    try:
        user = soft_delete_user(user_id, actor)
        if user.get("moodle_user_id"):
            moodle_suspend_user(user["moodle_user_id"])
        return user
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@management_router.get("/users/{user_id}/activity")
def get_activity(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    target = fetch_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_access_user(current_user, target):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
    return {"activity": get_user_activity(user_id)}


@management_router.get("/settings/system")
def get_settings(_: TokenData = Depends(require_admin)):
    if moodle_mode() == "live":
        return build_moodle_settings_snapshot()
    return get_system_settings()


@management_router.get("/notifications")
def get_my_notifications(current_user: TokenData = Depends(get_current_user)):
    return {"notifications": list_notifications(current_user.id)}
