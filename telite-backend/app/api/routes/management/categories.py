"""Category management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import TokenData, ensure_org_access, require_super_admin, resolve_org_scope
from app.db.engine import db_session
from app.repositories.course_repo import CategoryRepository, DuplicateResourceError
from app.repositories.user_repo import UserRepository
from app.api.routes.management.schemas import CategoryPayload
from app.api.routes.management.utils import org_id

categories_router = APIRouter(tags=["Category Management"])


@categories_router.get("/categories")
def get_categories(
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Get all categories for an organization."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    repo = CategoryRepository(db)
    cats = repo.list_by_org(scoped_org_id, include_archived=True)
    return {"categories": [cat.to_dict() for cat in cats]}


@categories_router.post("/categories")
def post_category(
    body: CategoryPayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Create a new category."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")

    payload = body.model_dump()
    scoped_org_id = payload.get("organization_id") or resolve_org_scope(current_user, org_id)
    
    try:
        repo = CategoryRepository(db)
        created = repo.create_category(
            name=payload["name"],
            org_id=scoped_org_id,
            slug=payload.get("slug"),
            description=payload.get("description"),
            admin_user_id=payload.get("admin_user_id"),
            accent_color=payload.get("accent_color", "#2563EB"),
            org_type=payload.get("org_type", "college"),
            planned_courses=payload.get("planned_courses", 0),
        )
        db.commit()
        return created.to_dict()
    except DuplicateResourceError as dre:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "code": "CATEGORY_NAME_EXISTS",
            "field": dre.field,
            "message": dre.message
        })
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@categories_router.patch("/categories/{category_id}")
def patch_category(
    category_id: str,
    body: CategoryPayload,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Update an existing category."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    repo = CategoryRepository(db)
    existing = repo.get_by_id(category_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, org_id(existing))
    try:
        updated = repo.update_category(existing, **body.model_dump(exclude_unset=True))
        db.commit()
        return updated.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@categories_router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: TokenData = Depends(require_super_admin),
    db: Session = Depends(db_session),
):
    """Archive a category (soft delete)."""
    user_repo = UserRepository(db)
    actor = user_repo.get_by_id(current_user.id)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
        
    repo = CategoryRepository(db)
    category = repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    ensure_org_access(current_user, org_id(category))
    try:
        from datetime import datetime
        category.status = "archived"
        category.archived_at = datetime.utcnow().isoformat()
        db.commit()
        return category.to_dict()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
