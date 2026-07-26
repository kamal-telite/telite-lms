"""Course management endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.api.auth import TokenData, ensure_org_access, require_admin, resolve_org_scope, get_current_user
from app.db.engine import db_session
from app.repositories.course_repo import CategoryRepository, CourseRepository, DuplicateResourceError
from app.repositories.user_repo import UserRepository
from app.core.storage_paths import media_upload_root
from app.api.routes.management.schemas import CoursePayload
from app.api.routes.management.utils import is_learner_role, is_category_admin_role, org_id

courses_router = APIRouter(tags=["Course Management"])


@courses_router.get("/categories/{category_slug}/courses")
def get_category_courses(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """Get all courses for a category."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    cat_repo = CategoryRepository(db)
    category = cat_repo.get_by_slug(category_slug, scoped_org_id)
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


@courses_router.post("/categories/{category_slug}/courses")
def post_course(
    category_slug: str,
    body: CoursePayload,
    org_id: int | None = Query(default=None, alias="orgId"),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Create a new course in a category."""
    scoped_org_id = resolve_org_scope(current_user, org_id)
    cat_repo = CategoryRepository(db)
    category = cat_repo.get_by_slug(category_slug, scoped_org_id)
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
    except DuplicateResourceError as dre:
        db.rollback()
        raise HTTPException(status_code=409, detail={
            "code": "COURSE_NAME_EXISTS",
            "field": dre.field,
            "message": dre.message
        })
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@courses_router.patch("/categories/{category_slug}/courses/{course_id}")
def patch_course(
    category_slug: str,
    course_id: str,
    body: CoursePayload,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Update an existing course."""
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


@courses_router.delete("/categories/{category_slug}/courses/{course_id}")
def delete_course(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Archive a course (soft delete)."""
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


@courses_router.post("/categories/{category_slug}/courses/{course_id}/cover")
async def upload_course_cover(
    category_slug: str,
    course_id: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Upload a cover image for a course."""
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    ensure_org_access(current_user, course.org_id)

    # 1. Validate file extension
    filename = file.filename or ""
    if "." not in filename:
        raise HTTPException(status_code=400, detail="Invalid filename (no extension)")
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(status_code=400, detail="Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP.")

    # 2. Validate file size (max 5 MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5 MB.")

    # 3. Save file
    org_dir = media_upload_root() / str(course.org_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    unique_id = uuid.uuid4().hex[:8]
    saved_name = f"course_cover_{course_id}_{unique_id}.{ext}"
    target_path = org_dir / saved_name
    
    with open(target_path, "wb") as f:
        f.write(contents)

    # 4. Update Course cover_image_url
    url_path = f"/uploads/media/{course.org_id}/{saved_name}"
    course.cover_image_url = url_path
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    return {"cover_image_url": url_path}


@courses_router.delete("/categories/{category_slug}/courses/{course_id}/cover")
def delete_course_cover(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Remove the cover image from a course."""
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    ensure_org_access(current_user, course.org_id)

    course.cover_image_url = None
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    return {"cover_image_url": None}


@courses_router.get("/courses/{course_id}/launch")
def launch_course(
    course_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    """Get the launch URL for a course."""
    return {"launch_url": f"/course/player/{course_id}", "status": "success"}
