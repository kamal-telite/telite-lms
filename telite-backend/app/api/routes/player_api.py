from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.course_module import CourseModule
from app.models.module_progress import ModuleProgress
from app.models.interactive_tracking import InteractiveTracking
from app.services.analytics_service import analytics_service

logger = logging.getLogger("telite.player")

player_router = APIRouter(prefix="/player", tags=["Native Player"])

class TrackingEvent(BaseModel):
    element: str
    value: str

class TrackingSyncRequest(BaseModel):
    module_id: int
    protocol: str  # 'scorm_12', 'scorm_2004', 'xapi'
    events: list[TrackingEvent]
    status: str | None = None
    score: float | None = None
    time_spent_seconds: int = 0

@player_router.post("/tracking")
def sync_tracking(
    request: TrackingSyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Unified endpoint for syncing SCORM/xAPI tracking state.
    Designed to accept batch sync queues from the frontend OfflineSyncManager.
    """
    module = db.query(CourseModule).filter(
        CourseModule.id == request.module_id, 
        CourseModule.org_id == current_user.org_id
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    # Get or create module progress
    progress = db.query(ModuleProgress).filter(
        ModuleProgress.module_id == module.id,
        ModuleProgress.user_id == current_user.id
    ).first()
    
    if not progress:
        progress = ModuleProgress(
            user_id=current_user.id,
            module_id=module.id,
            org_id=current_user.org_id,
            status=request.status or "in_progress",
            score=request.score,
            time_spent_seconds=request.time_spent_seconds
        )
        db.add(progress)
        db.flush() # get id
    else:
        if request.status:
            progress.status = request.status
        if request.score is not None:
            progress.score = request.score
        progress.time_spent_seconds = (progress.time_spent_seconds or 0) + request.time_spent_seconds

    # Process individual cmi/xapi tracking events
    for evt in request.events:
        tracking = db.query(InteractiveTracking).filter(
            InteractiveTracking.attempt_id == progress.id,
            InteractiveTracking.element == evt.element,
            InteractiveTracking.protocol == request.protocol
        ).first()
        
        if tracking:
            tracking.value = evt.value
        else:
            new_tracking = InteractiveTracking(
                attempt_id=progress.id,
                protocol=request.protocol,
                element=evt.element,
                value=evt.value,
                org_id=current_user.org_id
            )
            db.add(new_tracking)
            
        # Emit analytics event for interactions
        if evt.element.startswith("cmi.interactions") or request.protocol == "xapi":
            background_tasks.add_task(
                analytics_service.log_event,
                "INTERACTION_LOGGED",
                current_user.org_id,
                current_user.id,
                {"module_id": request.module_id, "protocol": request.protocol, "element": evt.element, "value": evt.value}
            )

    db.commit()
    
    # Note: Legacy Moodle sync triggers have been removed
    return {"success": True, "progress_status": progress.status}

@player_router.get("/modules/{module_id}/launch")
def get_launch_data(
    module_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Returns native content metadata or S3 signed URLs for SCORM/xAPI/H5P packages.
    No Moodle iframes.
    """
    module = db.query(CourseModule).filter(
        CourseModule.id == module_id, 
        CourseModule.org_id == current_user.org_id
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    # Log analytics
    background_tasks.add_task(
        analytics_service.log_event,
        "MODULE_VIEWED",
        current_user.org_id,
        current_user.id,
        {"module_id": module_id, "module_type": module.module_type, "title": module.title}
    )

    # In a real impl, we'd sign an S3 URL to the `imsmanifest.xml` or `h5p.json`
    launch_url = f"https://cdn.telite.io/tenant_{current_user.org_id}/modules/{module.id}/index.html"
    
    # Fetch existing tracking state to resume
    progress = db.query(ModuleProgress).filter(
        ModuleProgress.module_id == module.id,
        ModuleProgress.user_id == current_user.id
    ).first()
    
    tracking_state = {}
    if progress:
        tracks = db.query(InteractiveTracking).filter(InteractiveTracking.attempt_id == progress.id).all()
        for t in tracks:
            tracking_state[t.element] = t.value

    return {
        "module_type": module.module_type,
        "launch_url": launch_url,
        "resume_state": tracking_state,
        "status": progress.status if progress else "not_started"
    }
