from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, require_super_admin, resolve_org_scope
from sqlalchemy.orm import Session
from app.db.engine import db_session
from app.repositories.analytics_repo import AnalyticsRepository
from app.core.rbac import ROLE_PERMISSIONS, Permission


dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


@dashboard_router.get("/super-admin")
def get_super_admin_dashboard(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin), db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    analytics_repo = AnalyticsRepository(db)
    return analytics_repo.get_global_kpis(scoped_org_id)


@dashboard_router.get("/categories/{category_slug}/admin")
def get_category_admin_dashboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    if (current_user.role == "category_admin" or Permission.CAT_MANAGE_COURSES in ROLE_PERMISSIONS.get(current_user.role, set())) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    try:
        scoped_org_id = resolve_org_scope(current_user, org_id)
        ensure_org_access(current_user, scoped_org_id)
        analytics_repo = AnalyticsRepository(db)
        return analytics_repo.get_category_metrics(category_slug, org_id=scoped_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@dashboard_router.get("/categories/{category_slug}/stats")
def get_category_stats_dashboard(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session),
):
    if (current_user.role == "category_admin" or Permission.CAT_MANAGE_COURSES in ROLE_PERMISSIONS.get(current_user.role, set())) and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")
    try:
        scoped_org_id = resolve_org_scope(current_user, org_id)
        ensure_org_access(current_user, scoped_org_id)
        analytics_repo = AnalyticsRepository(db)
        return analytics_repo.get_stats_breakdown(category_slug, org_id=scoped_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@dashboard_router.get("/learner")
def get_learner_dashboard(current_user: TokenData = Depends(get_current_user), db: Session = Depends(db_session)):
    if not (current_user.role in ["learner", "student", "employee", "intern"] or Permission.LEARNER_VIEW_COURSES in ROLE_PERMISSIONS.get(current_user.role, set())):
        raise HTTPException(status_code=403, detail="Learner access required")
    try:
        analytics_repo = AnalyticsRepository(db)
        return analytics_repo.get_learner_summary(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
