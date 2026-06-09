from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import TokenData, ensure_org_access, get_current_user, require_admin, require_super_admin, resolve_org_scope
from app.db.engine import db_session
from app.repositories.course_repo import CategoryRepository, CourseRepository
from app.repositories.user_repo import UserRepository
from app.repositories.org_repo import OrgRepository
from app.repositories.invite_repo import InviteRepository
from app.repositories.notification_repo import NotificationRepository
from app.services.email import send_invitation_email

logger = logging.getLogger("telite.management")
management_router = APIRouter(tags=["Management"])

def is_admin_role(role: str) -> bool:
    return role in ("super_admin", "category_admin")

def is_category_admin_role(role: str) -> bool:
    return role == "category_admin"

def is_learner_role(role: str) -> bool:
    return role == "learner"

def is_tenant_super_admin_role(role: str) -> bool:
    return role == "super_admin"

def _org_id(record: Any) -> int | None:
    if not record:
        return None
    if isinstance(record, dict):
        return record.get("org_id") or record.get("organization_id")
    return getattr(record, "org_id", getattr(record, "organization_id", None))

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
    password: str | None = None
    username: str | None = None
    category_scope: str | None = None

class InviteAdminPayload(BaseModel):
    email: str
    role: str
    category_scope: str | None = None

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
class UserRolePayload(BaseModel):
    role: str
    category_scope: str | None = None

class UserActivePayload(BaseModel):
    is_active: bool

class AllowedDomainPayload(BaseModel):
    domain: str
    label: str

@management_router.get("/categories")
def get_categories(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    repo = CategoryRepository(db)
    cats = repo.list_by_org(scoped_org_id, include_archived=True)
    return {"categories": [cat.to_dict() for cat in cats]}

@management_router.post("/categories")
def post_category(
    body: CategoryPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    payload = body.model_dump()
    scoped_org_id = payload.get("organization_id") or resolve_org_scope(current_user, org_id)
    
    repo = CategoryRepository(db)
    existing = repo.get_by_slug(payload["slug"])
    if existing and existing.org_id == scoped_org_id:
        raise HTTPException(status_code=400, detail="Category slug already exists.")

    try:
        created = repo.create_category(
            name=payload["name"],
            org_id=scoped_org_id,
            slug=payload["slug"],
            description=payload.get("description"),
            admin_user_id=payload.get("admin_user_id"),
            accent_color=payload.get("accent_color", "#2563EB"),
            org_type=payload.get("org_type", "college"),
            planned_courses=payload.get("planned_courses", 0),
        )
        db.commit()
        return created.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.patch("/categories/{category_id}")
def patch_category(
    category_id: str,
    body: CategoryPayload,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    repo = CategoryRepository(db)
    existing = repo.get_by_id(category_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, _org_id(existing))
    try:
        updated = repo.update_category(existing, **body.model_dump(exclude_unset=True))
        db.commit()
        return updated.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    repo = CategoryRepository(db)
    category = repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, _org_id(category))
    try:
        from datetime import datetime
        category.status = "archived"
        category.archived_at = datetime.utcnow().isoformat()
        db.commit()
        return category.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.get("/admins")
def get_admins(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    user_repo = UserRepository(db)
    admins = user_repo.list_admins_by_org(scoped_org_id)
    return {"admins": [a.to_dict() for a in admins]}

@management_router.post("/admins")
def post_admin(
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    try:
        existing = user_repo.get_by_email(body.email)
        if existing:
            # Update existing
            existing.role = body.role
            existing.full_name = body.full_name
            if body.category_scope:
                existing.category_scope = body.category_scope
            if body.password:
                user_repo.update_password(existing, body.password)
            user = existing
        else:
            user = user_repo.create_user(
                email=body.email,
                full_name=body.full_name,
                role=body.role,
                org_id=scoped_org_id,
                password=body.password or "ChangeMe123!",
                category_scope=body.category_scope,
                username=body.username
            )
        db.commit()
        return user.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.patch("/admins/{user_id}")
def patch_admin(
    user_id: str,
    body: AdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    existing = user_repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    ensure_org_access(current_user, existing.org_id)
    try:
        existing.full_name = body.full_name
        existing.email = body.email
        existing.role = body.role
        if body.category_scope is not None:
            existing.category_scope = body.category_scope
        if body.username:
            existing.username = body.username
        if body.password:
            user_repo.update_password(existing, body.password)
        db.commit()
        return existing.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.post("/admins/invite", status_code=201)
def api_invite_admin(
    payload: InviteAdminPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    scoped_org_id = resolve_org_scope(current_user, org_id)
    org_repo = OrgRepository(db)
    org = org_repo.get_by_id(scoped_org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    try:
        invite_repo = InviteRepository(db)
        invitation = invite_repo.create_invitation(
            org_id=scoped_org_id,
            email=payload.email,
            role=payload.role,
            invited_by=actor.id,
            category_scope=payload.category_scope,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
        
    delivered = send_invitation_email(
        to_email=invitation.email,
        org_name=org.name,
        role=invitation.role,
        token=invitation.token,
        expires_at=invitation.expires_at.isoformat(),
    )
    
    try:
        invite_repo.record_delivery(invitation.id, delivered=delivered)
        db.commit()
    except:
        db.rollback()
    
    return {"message": "Invitation sent successfully", "invitation": invitation.to_dict()}

@management_router.delete("/admins/{user_id}")
def delete_admin(
    user_id: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    existing = user_repo.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    ensure_org_access(current_user, existing.org_id)
    try:
        db.delete(existing)
        db.commit()
        return {"status": "success"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.get("/categories/{category_slug}/courses")
def get_category_courses(
    category_slug: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    cat_repo = CategoryRepository(db)
    category = cat_repo.get_by_slug(category_slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, category.org_id)
    user_repo = UserRepository(db)
    viewer = user_repo.get_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
        
    if is_learner_role(viewer.role):
        if viewer.category_scope != category_slug:
            raise HTTPException(status_code=403, detail="You do not have access to this category.")
    elif is_category_admin_role(viewer.role) and viewer.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="Access denied")
        
    course_repo = CourseRepository(db)
    courses = course_repo.list_by_org(category.org_id, category_slug=category_slug)
    return {"courses": [c.to_dict() for c in courses]}

@management_router.post("/categories/{category_slug}/courses")
def post_course(
    category_slug: str,
    body: CoursePayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    cat_repo = CategoryRepository(db)
    category = cat_repo.get_by_slug(category_slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, category.org_id)
    
    course_repo = CourseRepository(db)
    try:
        payload = body.model_dump()
        payload["category_slug"] = category_slug
        payload["org_id"] = category.org_id
        course = course_repo.create_course(**payload)
        db.commit()
        return course.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.patch("/categories/{category_slug}/courses/{course_id}")
def patch_course(
    category_slug: str,
    course_id: str,
    body: CoursePayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    ensure_org_access(current_user, course.org_id)
    try:
        updated = course_repo.update_course(course, **body.model_dump(exclude_unset=True))
        db.commit()
        return updated.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.delete("/categories/{category_slug}/courses/{course_id}")
def delete_course(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    ensure_org_access(current_user, course.org_id)
    try:
        course.status = "archived"
        db.commit()
        return course.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

@management_router.get("/courses/{course_id}/launch")
def launch_course(
    course_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    # Native player replaces moodle. Just return a native launch URL.
    return {"launch_url": f"/course/player/{course_id}", "status": "success"}

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
    db: Session = Depends(db_session),
):
    scoped_org_id = resolve_org_scope(current_user, org_id)
    user_repo = UserRepository(db)
    
    if is_category_admin_role(current_user.role):
        category_slug = current_user.category_scope
        if role and is_tenant_super_admin_role(role):
            raise HTTPException(status_code=403, detail="Category admins cannot view super admin users.")
            
    offset = (page - 1) * page_size
    users = user_repo.list_by_org(scoped_org_id, role=role, search=query, limit=page_size, offset=offset)
    
    # Optional category filtering
    if category_slug:
        users = [u for u in users if u.category_scope == category_slug]
        
    return {"users": [u.to_dict() for u in users], "total": len(users)}

def _can_access_user(viewer: TokenData, target: Any) -> bool:
    if viewer.is_platform_admin:
        return True
    if viewer.org_id is None or _org_id(target) != viewer.org_id:
        return False
    if is_tenant_super_admin_role(viewer.role):
        return True
    if is_category_admin_role(viewer.role):
        return target.category_scope == viewer.category_scope or is_admin_role(target.role)
    return viewer.id == target.id

@management_router.get("/users/{user_id}")
def get_user(
    user_id: str, 
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_access_user(current_user, user):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
    return user.to_dict()

@management_router.patch("/users/{user_id}/role")
def patch_user_role(
    user_id: str,
    body: UserRolePayload,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, target.org_id)
    try:
        updated = user_repo.update_role(target, role=body.role, category_scope=body.category_scope)
        db.commit()
        return updated.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

@management_router.patch("/users/{user_id}/activate")
def patch_user_active(
    user_id: str,
    body: UserActivePayload,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, target.org_id)
    try:
        updated = user_repo.set_active(target, is_active=body.is_active)
        db.commit()
        return updated.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))

@management_router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_org_access(current_user, target.org_id)
    try:
        db.delete(target)
        db.commit()
        return {"status": "success"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@management_router.get("/users/{user_id}/activity")
def get_activity(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    user_repo = UserRepository(db)
    target = user_repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if not _can_access_user(current_user, target):
        raise HTTPException(status_code=403, detail="You do not have access to this user.")
        
    from app.repositories.analytics_repo import AnalyticsRepository
    analytics_repo = AnalyticsRepository(db)
    summary = analytics_repo.get_learner_summary(target)
    
    return {"activity": {
        "login_count": 0,
        "courses_completed": summary["courses_completed"],
        "certificates_earned": summary["certificates_earned"],
        "total_time_spent_hours": summary["time_spent_hours"]
    }}

@management_router.get("/settings/system")
def get_settings(current_user: TokenData = Depends(require_admin), db: Session = Depends(db_session)):
    org_repo = OrgRepository(db)
    org = org_repo.get_by_id(current_user.org_id)
    if not org:
        return {}
    
    return {
        "allowed_domains": [],
        "branding": org_repo.get_branding(org.slug)
    }

@management_router.post("/settings/domains")
def add_domain(
    body: AllowedDomainPayload,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session)
):
    # This feature is being deprecated in favor of email allowlists
    return {"status": "success", "domain": body.domain, "label": body.label}

@management_router.delete("/settings/domains/{domain:path}")
def remove_domain(
    domain: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session)
):
    return {"status": "success"}

@management_router.get("/notifications")
def get_my_notifications(current_user: TokenData = Depends(get_current_user), db: Session = Depends(db_session)):
    repo = NotificationRepository(db)
    notifs = repo.list_for_user(current_user.id)
    return {"notifications": [n.to_dict() for n in notifs]}
