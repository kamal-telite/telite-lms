"""Course management endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.api.auth import TokenData, ensure_org_access, require_admin, resolve_org_scope, get_current_user
from app.db.engine import db_session
from app.repositories.course_repo import CategoryRepository, CourseRepository, DuplicateResourceError
from app.repositories.user_repo import UserRepository
from app.core.storage_paths import media_upload_root
from app.api.routes.management.schemas import CoursePayload
from app.api.routes.management.utils import is_learner_role, is_category_admin_role, org_id
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.learning_session import LearningSession
from app.models.user import User

courses_router = APIRouter(tags=["Course Management"])


def _ensure_category_admin_category_access(
    current_user: TokenData,
    category_slug: str,
    db: Session,
    org_id_value: int | None = None,
):
    scoped_org_id = resolve_org_scope(current_user, org_id_value)
    cat_repo = CategoryRepository(db)
    category = cat_repo.get_by_slug(category_slug, scoped_org_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    ensure_org_access(current_user, category.org_id)
    user_repo = UserRepository(db)
    viewer = user_repo.get_by_id(current_user.id)
    if not viewer:
        raise HTTPException(status_code=404, detail="Viewer not found")
    if is_category_admin_role(viewer.role) and viewer.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="Access denied")
    if is_learner_role(viewer.role):
        raise HTTPException(status_code=403, detail="Access denied")
    return category


def _archived_course_payload(course: Course) -> dict:
    deleted_at = course.updated_at or course.created_at
    return {
        "id": course.id,
        "category_slug": course.category_slug,
        "category": course.category_slug,
        "name": course.name,
        "status": course.status,
        "cover_image_url": course.cover_image_url,
        "deleted_at": deleted_at.isoformat() if deleted_at else None,
        "deleted_by": None,
    }


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


@courses_router.get("/categories/{category_slug}/courses/archived")
def get_archived_category_courses(
    category_slug: str,
    org_id: int | None = Query(default=None, alias="orgId"),
    search: str | None = Query(default=None),
    sort: str = Query(default="newest", pattern="^(newest|oldest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """List archived courses for the current category admin/category."""
    category = _ensure_category_admin_category_access(current_user, category_slug, db, org_id)
    base_stmt = select(Course).where(
        Course.org_id == category.org_id,
        Course.category_slug == category_slug,
        Course.status == "archived",
    )
    if search:
        base_stmt = base_stmt.where(Course.name.ilike(f"%{search.strip()}%"))

    total = db.execute(select(func.count()).select_from(base_stmt.subquery())).scalar_one()
    order_column = func.coalesce(Course.updated_at, Course.created_at)
    if sort == "oldest":
        base_stmt = base_stmt.order_by(order_column.asc(), Course.name.asc())
    else:
        base_stmt = base_stmt.order_by(order_column.desc(), Course.name.asc())
    courses = db.execute(
        base_stmt.limit(page_size).offset((page - 1) * page_size)
    ).scalars().all()
    return {
        "courses": [_archived_course_payload(course) for course in courses],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@courses_router.post("/categories/{category_slug}/courses/{course_id}/restore")
def restore_archived_course(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Restore an archived course."""
    import logging
    logger = logging.getLogger("telite.api")
    
    logger.info(f"[RESTORE] Starting restore - category_slug={category_slug}, course_id={course_id}, user_id={current_user.id}")
    
    try:
        category = _ensure_category_admin_category_access(current_user, category_slug, db)
        logger.info(f"[RESTORE] Category access verified - category_id={category.id}, org_id={category.org_id}")
    except HTTPException as exc:
        logger.error(f"[RESTORE] Category access failed: {exc.detail}")
        raise
    
    try:
        course = db.execute(
            select(Course).where(
                Course.id == course_id,
                Course.org_id == category.org_id,
                Course.category_slug == category_slug,
            )
        ).scalar_one_or_none()
        logger.info(f"[RESTORE] Course lookup result: course={course is not None}, course_id={course_id}")
    except Exception as exc:
        logger.error(f"[RESTORE] Course lookup exception: {str(exc)}")
        raise HTTPException(status_code=400, detail=f"Course lookup failed: {str(exc)}")
    
    if not course:
        logger.error(f"[RESTORE] Course not found - course_id={course_id}, org_id={category.org_id}, category_slug={category_slug}")
        raise HTTPException(status_code=404, detail="Course not found")
    
    logger.info(f"[RESTORE] Course found - id={course.id}, status={course.status}, name={course.name}")
    
    if course.status != "archived":
        logger.error(f"[RESTORE] Course not archived - current_status={course.status}")
        raise HTTPException(status_code=400, detail="Course is not archived")

    try:
        logger.info(f"[RESTORE] Setting course status to 'active'")
        course.status = "active"
        logger.info(f"[RESTORE] Committing transaction")
        db.commit()
        logger.info(f"[RESTORE] Transaction committed successfully")
        return course.to_dict()
    except Exception as exc:
        logger.error(f"[RESTORE] Exception during restore: {str(exc)}", exc_info=True)
        db.rollback()
        logger.error(f"[RESTORE] Transaction rolled back")
        raise HTTPException(status_code=400, detail=str(exc))


@courses_router.delete("/categories/{category_slug}/courses/{course_id}/permanent")
def permanently_delete_archived_course(
    category_slug: str,
    course_id: str,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(db_session),
):
    """Permanently delete an archived course."""
    import logging
    logger = logging.getLogger("telite.api")
    
    logger.info(f"[PERMANENT DELETE] Starting permanent delete - category_slug={category_slug}, course_id={course_id}, user_id={current_user.id}")
    
    try:
        category = _ensure_category_admin_category_access(current_user, category_slug, db)
        logger.info(f"[PERMANENT DELETE] Category access verified - category_id={category.id}, org_id={category.org_id}")
    except HTTPException as exc:
        logger.error(f"[PERMANENT DELETE] Category access failed: {exc.detail}")
        raise
    
    try:
        course = db.execute(
            select(Course).where(
                Course.id == course_id,
                Course.org_id == category.org_id,
                Course.category_slug == category_slug,
            )
        ).scalar_one_or_none()
        logger.info(f"[PERMANENT DELETE] Course lookup result: course={course is not None}, course_id={course_id}")
    except Exception as exc:
        logger.error(f"[PERMANENT DELETE] Course lookup exception: {str(exc)}")
        raise HTTPException(status_code=400, detail=f"Course lookup failed: {str(exc)}")
    
    if not course:
        logger.error(f"[PERMANENT DELETE] Course not found - course_id={course_id}, org_id={category.org_id}, category_slug={category_slug}")
        raise HTTPException(status_code=404, detail="Course not found")
    
    logger.info(f"[PERMANENT DELETE] Course found - id={course.id}, status={course.status}, name={course.name}")
    
    if course.status != "archived":
        logger.error(f"[PERMANENT DELETE] Course not archived - current_status={course.status}")
        raise HTTPException(status_code=400, detail="Only archived courses can be permanently deleted")

    try:
        logger.info(f"[PERMANENT DELETE] Starting cascade delete operations")
        
        # Execute subqueries to get actual ID lists
        module_ids = db.execute(select(CourseModule.id).where(CourseModule.course_id == course_id)).scalars().all()
        section_ids = db.execute(select(CourseSection.id).where(CourseSection.course_id == course_id)).scalars().all()
        block_ids = db.execute(select(LessonBlock.id).where(LessonBlock.module_id.in_(module_ids))).scalars().all() if module_ids else []
        
        logger.info(f"[PERMANENT DELETE] Dependent records found - modules={len(module_ids)}, sections={len(section_ids)}, blocks={len(block_ids)}")
        
        # Clear user references to this course
        user_update_result = db.execute(update(User).where(User.current_course_id == course_id).values(current_course_id=None))
        logger.info(f"[PERMANENT DELETE] User references cleared - rows_affected={user_update_result.rowcount}")
        
        # Clear learning session references before deletion
        session_update_result = db.execute(update(LearningSession).where(LearningSession.course_id == course_id).values(module_id=None, section_id=None, block_id=None))
        logger.info(f"[PERMANENT DELETE] Learning session references cleared - rows_affected={session_update_result.rowcount}")
        
        # Delete in correct order to respect foreign key constraints
        # Delete blocks first (they reference modules)
        if block_ids:
            blocks_deleted = db.execute(delete(LessonBlock).where(LessonBlock.id.in_(block_ids)))
            logger.info(f"[PERMANENT DELETE] Lesson blocks deleted - rows_affected={blocks_deleted.rowcount}")
        
        # Delete modules (they reference courses)
        if module_ids:
            modules_deleted = db.execute(delete(CourseModule).where(CourseModule.course_id == course_id))
            logger.info(f"[PERMANENT DELETE] Course modules deleted - rows_affected={modules_deleted.rowcount}")
        
        # Delete sections (they reference courses)
        if section_ids:
            sections_deleted = db.execute(delete(CourseSection).where(CourseSection.course_id == course_id))
            logger.info(f"[PERMANENT DELETE] Course sections deleted - rows_affected={sections_deleted.rowcount}")
        
        # Finally delete the course
        logger.info(f"[PERMANENT DELETE] Deleting course from database")
        
        # -------------------------------------------------------------
        # NOTIFICATION: Course Deleted
        # -------------------------------------------------------------
        from app.services.notification_service import NotificationService
        notif_service = NotificationService(db)
        context = {
            "course_id": course.id,
            "course_name": course.name
        }
        
        # Notify the user performing the deletion
        notif_service.emit_event("course.deleted", course.org_id, context, current_user.id)
        
        db.delete(course)
        logger.info(f"[PERMANENT DELETE] Course deleted, committing transaction")
        
        db.commit()
        logger.info(f"[PERMANENT DELETE] Transaction committed successfully")
        
        return {"status": "deleted", "course_id": course_id}
    except Exception as exc:
        logger.error(f"[PERMANENT DELETE] Exception during delete: {str(exc)}", exc_info=True)
        db.rollback()
        logger.error(f"[PERMANENT DELETE] Transaction rolled back")
        raise HTTPException(status_code=400, detail=str(exc))


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
        
        # -------------------------------------------------------------
        # NOTIFICATION: Course Created
        # -------------------------------------------------------------
        from app.services.notification_service import NotificationService
        from app.models.user import User
        from sqlalchemy import or_
        
        notif_service = NotificationService(db)
        context = {
            "course_id": course.id,
            "course_name": course.name,
            "creator_name": current_user.full_name
        }
        
        # Notify Author
        notif_service.emit_event("course.created", course.org_id, context, current_user.id)
        
        # Notify Admins (Super Admins + this category's Category Admins)
        from sqlalchemy import select
        stmt = select(User.id).where(
            User.org_id == course.org_id,
            User.is_active == True,
            User.id != current_user.id,
            or_(User.role == "super_admin", 
                (User.role == "category_admin") & (User.category_scope == category_slug))
        )
        admin_ids = db.scalars(stmt).all()
        
        for uid in admin_ids:
            notif_service.emit_event("course.created", course.org_id, context, uid)
            
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
        payload = body.model_dump(exclude_unset=True)
        
        # Determine if learner-visible changes are made
        learner_visible_fields = ["name", "description", "tier", "cover_image_url", "prerequisite_course_id", "price_paise"]
        has_visible_changes = any(
            field in payload and getattr(course, field) != payload[field]
            for field in learner_visible_fields
        )
        
        updated = course_repo.update_course(course, **payload)
        
        # -------------------------------------------------------------
        # NOTIFICATION: Course Updated
        # -------------------------------------------------------------
        import time
        from app.services.notification_service import NotificationService
        notif_service = NotificationService(db)
        context = {
            "course_id": updated.id,
            "course_name": updated.name,
            "timestamp": str(time.time())
        }
        
        # Notify the author (the user who submitted it for review / originally created it)
        # To simplify, we can notify the current_user if they are not the only one, or find the course creator.
        # Let's just notify current_user as an acknowledgment for now.
        notif_service.emit_event("course.updated", updated.org_id, context, current_user.id)
        
        # Notify learners if published and visible changes occurred
        if updated.status == "published" and has_visible_changes:
            from app.workers.notification_tasks import dispatch_fanout_task
            dispatch_fanout_task.delay(
                event_name="course.updated",
                org_id=updated.org_id,
                context=context,
                audience={
                    "type": "course_enrolled",
                    "course_id": updated.id
                }
            )
            
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
        
        # -------------------------------------------------------------
        # NOTIFICATION: Course Archived
        # -------------------------------------------------------------
        from app.services.notification_service import NotificationService
        notif_service = NotificationService(db)
        context = {
            "course_id": course.id,
            "course_name": course.name
        }
        
        # Notify author
        notif_service.emit_event("course.archived", course.org_id, context, current_user.id)
        
        # Notify enrolled learners via fanout
        from app.workers.notification_tasks import dispatch_fanout_task
        dispatch_fanout_task.delay(
            event_name="course.archived",
            org_id=course.org_id,
            context=context,
            audience={
                "type": "course_enrolled",
                "course_id": course.id
            }
        )
        
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
