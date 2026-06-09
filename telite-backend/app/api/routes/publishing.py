import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.repositories.publishing_repo import PublishingRepository

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

    pub_repo.update_course_status(course, new_status)

    version = None
    if action == "publish":
        existing = pub_repo.get_versions(course_id, current_user.org_id)
        next_number = existing[0].version_number + 1 if existing else 1
        parent_version_id = existing[0].id if existing else None
        version = pub_repo.create_version(
            course_id, current_user.org_id, next_number, parent_version_id
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

    return {
        "success": True,
        "status": new_status,
        "version": version.to_dict() if version else None,
    }


# -----------------------------------------------------------------------------
# 2. Version Manager
# -----------------------------------------------------------------------------

@publishing_router.get("/courses/{course_id}/versions", dependencies=[Depends(require_admin)])
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
    pub_repo = PublishingRepository(db)
    course = pub_repo.get_course(course_id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = pub_repo.get_versions(course_id, current_user.org_id)
    next_number = existing[0].version_number + 1 if existing else 1
    
    version = pub_repo.create_version(
        course_id, current_user.org_id, next_number, request.parent_version_id
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

@publishing_router.post("/courses/{course_id}/versions/{version_id}/rollback", dependencies=[Depends(require_admin)])
def rollback_version(
    course_id: str,
    version_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    pub_repo = PublishingRepository(db)
    target_version = pub_repo.get_version(version_id, current_user.org_id)
    if not target_version:
        raise HTTPException(status_code=404, detail="Version not found")

    # The actual deep rollback logic of sections/modules/blocks would map the target_version structures
    # into the active draft pointers. For Stage 4, we log the rollback and simulate the pointer update.

    pub_repo.log_activity(
        course_id, 
        current_user.id, 
        current_user.org_id, 
        "COURSE_ROLLED_BACK", 
        json.dumps({"target_version_id": version_id, "target_version_number": target_version.version_number})
    )
    db.commit()
    return {"success": True, "message": f"Rolled back to version {target_version.version_number}"}
