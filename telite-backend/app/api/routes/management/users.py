"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.api.auth import TokenData, require_admin, resolve_org_scope, get_current_user
from app.db.engine import db_session
from app.repositories.user_repo import UserRepository
from app.repositories.analytics import AnalyticsRepository
from app.api.routes.management.utils import (
    is_category_admin_role,
    can_access_user,
    SUPER_ADMIN_VISIBLE_ROLES,
    CATEGORY_ADMIN_VISIBLE_ROLES,
)

users_router = APIRouter(tags=["User Management"])


@users_router.get("/users")
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
    db: Session = Depends(db_session),
):
    """Get users with filtering and pagination."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    user_repo = UserRepository(db)
    visible_roles = None
    
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
        visible_roles = CATEGORY_ADMIN_VISIBLE_ROLES
        if role and role not in visible_roles:
            raise HTTPException(status_code=403, detail="Category admins cannot view that user role.")
    elif not current_user.is_platform_admin:
        visible_roles = SUPER_ADMIN_VISIBLE_ROLES
        if role and role not in visible_roles:
            raise HTTPException(status_code=403, detail="Super admins cannot view platform admin users.")

    from app.models.user import User

    offset = (page - 1) * page_size
    stmt = select(User).where(User.org_id == scoped_org_id)
    
    if role:
        stmt = stmt.where(User.role == role)
    elif visible_roles:
        stmt = stmt.where(User.role.in_(visible_roles))
        
    if not current_user.is_platform_admin:
        stmt = stmt.where(User.is_platform_admin == False)
        
    if query:
        search_filter = f"%{query}%"
        stmt = stmt.where(or_(
            User.full_name.ilike(search_filter),
            User.email.ilike(search_filter),
            User.username.ilike(search_filter)
        ))
        
    if category_slug:
        stmt = stmt.where(User.category_scope == category_slug)

    total = len(db.scalars(stmt).all())
    stmt = stmt.limit(page_size).offset(offset)
    users = db.scalars(stmt).all()
        
    return {"users": [u.to_dict() for u in users], "total": total}


@users_router.get("/users/{user_id}")
def get_user(
    user_id: str, 
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session)
):
    """Get a specific user by ID."""
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not can_access_user(current_user, target):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
        
    from app.repositories.analytics import AnalyticsRepository
    analytics_repo = AnalyticsRepository(db)
    summary = analytics_repo.get_learner_summary(target)
    
    return {"activity": {
        "login_count": 0,
        "courses_completed": summary["courses_completed"],
        "certificates_earned": summary["certificates_earned"],
        "total_time_spent_hours": summary["time_spent_hours"]
    }}


@users_router.patch("/users/{user_id}/role")
def patch_user_role(
    user_id: str,
    body: dict,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Update a user's role."""
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not can_access_user(current_user, target):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
        
    try:
        user_repo.update(target, **body)
        db.commit()
        return target.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@users_router.patch("/users/{user_id}/active")
def patch_user_active(
    user_id: str,
    body: dict,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Update a user's active status."""
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not can_access_user(current_user, target):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
        
    try:
        user_repo.update(target, **body)
        db.commit()
        return target.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
