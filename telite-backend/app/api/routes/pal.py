from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, resolve_org_scope
from app.services.store import (
    fetch_user_by_id,
    get_pal_distribution,
    get_pal_user_detail,
    is_category_admin_role,
    is_learner_role,
    list_pal_leaderboard,
    recompute_pal,
)


pal_router = APIRouter(prefix="/pal", tags=["PAL"])


@pal_router.get("/leaderboard/{category_slug}")
def get_leaderboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
):
    if is_category_admin_role(current_user.role) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"leaderboard": list_pal_leaderboard(category_slug, org_id=scoped_org_id)}


@pal_router.get("/users/{user_id}")
def get_pal_user(user_id: str, current_user: TokenData = Depends(get_current_user)):
    if is_learner_role(current_user.role) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own PAL detail.")
    try:
        target = fetch_user_by_id(user_id)
        if not target:
            raise ValueError("User not found.")
        ensure_org_access(current_user, target.get("org_id") or target.get("organization_id"))
        return get_pal_user_detail(user_id, org_id=None if current_user.is_platform_admin else current_user.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@pal_router.get("/distribution/{category_slug}")
def get_distribution(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
):
    if is_category_admin_role(current_user.role) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    scoped_org_id = resolve_org_scope(current_user, org_id)
    return {"distribution": get_pal_distribution(category_slug, org_id=scoped_org_id)}


@pal_router.post("/compute")
def post_compute(
    category_slug: str | None = None,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
    return recompute_pal(category_slug, org_id=scoped_org_id)
