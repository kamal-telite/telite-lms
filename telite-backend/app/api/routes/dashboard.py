from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, require_super_admin, resolve_org_scope
from app.integrations.moodle_bridge import moodle_mode
from app.integrations.moodle_reports import build_super_admin_dashboard_from_moodle
from app.services.store import (
    build_category_admin_dashboard,
    build_learner_dashboard,
    build_stats_dashboard,
    build_super_admin_dashboard,
    is_category_admin_role,
    is_learner_role,
)


dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


@dashboard_router.get("/super-admin")
def get_super_admin_dashboard(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    if moodle_mode() == "live":
        return build_super_admin_dashboard_from_moodle()
    return build_super_admin_dashboard(scoped_org_id)


@dashboard_router.get("/categories/{category_slug}/admin")
def get_category_admin_dashboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    if is_category_admin_role(current_user.role) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    try:
        scoped_org_id = resolve_org_scope(current_user, org_id)
        ensure_org_access(current_user, scoped_org_id)
        return build_category_admin_dashboard(category_slug, org_id=scoped_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@dashboard_router.get("/categories/{category_slug}/stats")
def get_category_stats_dashboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
):
    if is_category_admin_role(current_user.role) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    try:
        scoped_org_id = resolve_org_scope(current_user, org_id)
        ensure_org_access(current_user, scoped_org_id)
        return build_stats_dashboard(category_slug, org_id=scoped_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@dashboard_router.get("/learner")
def get_learner_dashboard(current_user: TokenData = Depends(get_current_user)):
    if not is_learner_role(current_user.role):
        raise HTTPException(status_code=403, detail="Learner access required")
    try:
        return build_learner_dashboard(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
