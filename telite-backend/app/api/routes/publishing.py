import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.models.course_review import CourseReview
from app.repositories.publishing_repo import PublishingRepository
from app.services.audit_service import AuditService
from app.core.permissions import check_capability, require_capability

publishing_router = APIRouter(prefix="/authoring/publishing", tags=["Publishing Gateway"])

# -----------------------------------------------------------------------------
# 1. Publishing Workflow Engine
# -----------------------------------------------------------------------------

class WorkflowActionRequest(BaseModel):
    action: str  # submit_for_review, approve, reject, publish, archive
    notes: Optional[str] = None

@publishing_router.post("/courses/{course_id}/workflow", dependencies=[Depends(require_admin)])
def execute_workflow_action(
    course_id: str,
    request: WorkflowActionRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    pub_repo = PublishingRepository(db)
    course = pub_repo.get_course(course_id, current_user.org_id)
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    action = request.action
    log_action = ""
    new_status = ""
    previous_status = course.status

    if action == "submit_for_review":
        new_status = "review"
        log_action = "COURSE_SUBMITTED"
    elif action == "approve":
        new_status = "approved"
        log_action = "COURSE_APPROVED"
    elif action == "reject":
        new_status = "draft"
        log_action = "COURSE_REJECTED"
    elif action == "publish":
        new_status = "published"
        log_action = "COURSE_PUBLISHED"
    elif action == "archive":
        new_status = "archived"
        log_action = "COURSE_ARCHIVED"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    # Verify Capabilities
    if action == "submit_for_review":
        check_capability(db, current_user, "course.submit")
    elif action == "approve":
        check_capability(db, current_user, "course.approve")
    elif action == "reject":
        check_capability(db, current_user, "course.reject")
    elif action == "publish":
        check_capability(db, current_user, "course.publish")
    elif action == "archive":
        check_capability(db, current_user, "course.archive")

    AuditService.log(db, current_user.org_id, current_user.id, "course", course_id, log_action.lower().replace("_", "."), course_id)

    if action in ["submit_for_review", "publish"]:
        from app.services.validation.engine import ValidationEngine
        val_engine = ValidationEngine(db)
        val_result = val_engine.run(course_id, current_user.org_id)
        if val_result.summary.errors > 0:
            raise HTTPException(status_code=400, detail=f"Cannot proceed. Course has {val_result.summary.errors} validation errors.")

    pub_repo.update_course_status(course, new_status)
    review = CourseReview(
        course_id=course_id,
        org_id=current_user.org_id,
        action=action,
        from_status=previous_status,
        to_status=new_status,
        notes=request.notes,
        reviewed_by=current_user.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(review)

    version = None
    if action == "publish":
        existing = pub_repo.get_versions(course_id, current_user.org_id)
        next_number = existing[0].version_number + 1 if existing else 1
        parent_version_id = existing[0].id if existing else None
        snapshot = pub_repo.build_snapshot(course_id, current_user.org_id)
        version = pub_repo.create_version(
            course_id, current_user.org_id, next_number, parent_version_id, snapshot
        )
        pub_repo.update_version_status(version, "published", current_user.id)
    
    pub_repo.log_activity(
        course_id, 
        current_user.id, 
        current_user.org_id, 
        log_action, 
        json.dumps({"notes": request.notes})
    )
    db.commit()
    db.refresh(review)

    return {
        "success": True,
        "status": new_status,
        "version": version.to_dict() if version else None,
        "review": review.to_dict(),
    }


@publishing_router.get("/courses/{course_id}/reviews", dependencies=[Depends(require_admin)])
def list_course_reviews(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    pub_repo = PublishingRepository(db)
    course = pub_repo.get_course(course_id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    reviews = db.execute(
        select(CourseReview)
        .where(CourseReview.course_id == course_id, CourseReview.org_id == current_user.org_id)
        .order_by(CourseReview.reviewed_at.desc(), CourseReview.id.desc())
    ).scalars().all()
    return {"reviews": [review.to_dict() for review in reviews]}


# -----------------------------------------------------------------------------
# 2. Version Manager
# -----------------------------------------------------------------------------

@publishing_router.get("/courses/{course_id}/versions", dependencies=[Depends(require_capability("version.view"))])
def list_versions(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    pub_repo = PublishingRepository(db)
    versions = pub_repo.get_versions(course_id, current_user.org_id)
    return {"versions": [v.to_dict() for v in versions]}

class CreateVersionRequest(BaseModel):
    parent_version_id: Optional[int] = None

@publishing_router.post("/courses/{course_id}/versions", dependencies=[Depends(require_admin)])
def create_version(
    course_id: str,
    request: CreateVersionRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    check_capability(db, current_user, "version.create")
    pub_repo = PublishingRepository(db)
    course = pub_repo.get_course(course_id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = pub_repo.get_versions(course_id, current_user.org_id)
    next_number = existing[0].version_number + 1 if existing else 1
    
    snapshot = pub_repo.build_snapshot(course_id, current_user.org_id)
    version = pub_repo.create_version(
        course_id, current_user.org_id, next_number, request.parent_version_id, snapshot
    )
    
    pub_repo.log_activity(
        course_id, 
        current_user.id, 
        current_user.org_id, 
        "VERSION_CREATED", 
        json.dumps({"version_number": next_number})
    )
    db.commit()
    return {"success": True, "version": version.to_dict()}

@publishing_router.post("/courses/{course_id}/versions/{version_id}/restore", dependencies=[Depends(require_admin)])
def restore_course_version(
    course_id: str,
    version_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    check_capability(db, current_user, "version.rollback")
    
    pub_repo = PublishingRepository(db)
    target_version = pub_repo.get_version(version_id, current_user.org_id)
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")

    if target_version.course_id != course_id:
        raise HTTPException(status_code=404, detail="Version not found for this course")
    if not target_version.snapshot_json:
        raise HTTPException(status_code=400, detail="This version does not contain a restorable snapshot")

    restore_summary = pub_repo.restore_snapshot(
        course_id,
        current_user.org_id,
        target_version.snapshot_json,
        current_user.id,
    )

    pub_repo.log_activity(
        course_id, 
        current_user.id, 
        current_user.org_id, 
        "COURSE_ROLLED_BACK", 
        json.dumps({
            "target_version_id": version_id,
            "target_version_number": target_version.version_number,
            "restore_summary": restore_summary,
        })
    )
    db.commit()
    return {
        "success": True,
        "message": f"Rolled back to version {target_version.version_number}",
        "restore_summary": restore_summary,
    }

@publishing_router.get("/courses/{course_id}/versions/{left_version_id}/compare/{right_version_id}", dependencies=[Depends(require_capability("version.view"))])
def compare_versions(
    course_id: str,
    left_version_id: str,
    right_version_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    from app.services.diff_service import DiffService
    pub_repo = PublishingRepository(db)

    if left_version_id == "current":
        left_snapshot = pub_repo.build_snapshot(course_id, current_user.org_id)
        left_dict = {"version_number": "Draft"}
    else:
        left = pub_repo.get_version(int(left_version_id), current_user.org_id)
        if not left or left.course_id != course_id:
            raise HTTPException(status_code=404, detail="Version not found")
        left_snapshot = left.snapshot_json
        left_dict = left.to_dict()

    if right_version_id == "current":
        right_snapshot = pub_repo.build_snapshot(course_id, current_user.org_id)
        right_dict = {"version_number": "Draft"}
    else:
        right = pub_repo.get_version(int(right_version_id), current_user.org_id)
        if not right or right.course_id != course_id:
            raise HTTPException(status_code=404, detail="Version not found")
        right_snapshot = right.snapshot_json
        right_dict = right.to_dict()

    pub_repo.snapshot_summary(left_snapshot)
    pub_repo.snapshot_summary(right_snapshot)
    
    diff = DiffService.compute(left_snapshot, right_snapshot)
    
    return {
        "summary": diff["summary"],
        "changes": diff["events"],
        "left_version": left_dict,
        "right_version": right_dict
    }
