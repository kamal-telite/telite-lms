from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user
from app.core.storage_paths import media_upload_root
from app.db.engine import db_session
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_version import CourseVersion
from app.models.interactive_tracking import InteractiveTracking
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.module_progress import ModuleProgress
from app.repositories.enrollment_repo import EnrollmentRepository
from app.services.analytics_service import analytics_service
from app.services.h5p_service import (
    assert_h5p_asset,
    resolve_h5p_extract_dir,
    safe_h5p_file_path,
)

logger = logging.getLogger("telite.player")

player_router = APIRouter(prefix="/player", tags=["Native Player"])


def _uploads_root():
    return media_upload_root()


def _published_snapshot_references_asset(snapshot: dict | None, asset_id: int, asset_version: int | None) -> bool:
    if not isinstance(snapshot, dict):
        return False
    for section in snapshot.get("sections") or []:
        for module in section.get("modules") or []:
            for block in module.get("blocks") or []:
                settings = block.get("settings") or block.get("metadata_json") or {}
                block_asset_id = block.get("media_asset_id") or settings.get("asset_id")
                block_version = settings.get("asset_version")
                if block_asset_id == asset_id and (asset_version is None or block_version == asset_version):
                    return True
    return False


def _has_h5p_playback_access(
    db: Session,
    *,
    current_user: TokenData,
    asset_id: int,
    asset_version: int | None,
) -> bool:
    if current_user.role in ("super_admin", "category_admin") or current_user.is_platform_admin:
        return True

    enrollment_repo = EnrollmentRepository(db)
    live_courses = (
        db.query(Course.id)
        .join(CourseModule, CourseModule.course_id == Course.id)
        .join(LessonBlock, LessonBlock.module_id == CourseModule.id)
        .filter(
            Course.org_id == current_user.org_id,
            Course.status.in_(("active", "published")),
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
            LessonBlock.org_id == current_user.org_id,
            LessonBlock.media_asset_id == asset_id,
            LessonBlock.deleted_at.is_(None),
        )
        .distinct()
        .all()
    )
    for (course_id,) in live_courses:
        if enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
            return True

    published_versions = db.query(CourseVersion).filter(
        CourseVersion.org_id == current_user.org_id,
        CourseVersion.status == "published",
    ).all()
    for version in published_versions:
        if (
            _published_snapshot_references_asset(version.snapshot_json, asset_id, asset_version)
            and enrollment_repo.has_access(current_user.id, version.course_id, current_user.org_id)
        ):
            return True

    return False

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


@player_router.get("/h5p/{asset_id}/versions/{asset_version}")
@player_router.get("/h5p/{asset_id}/versions/{asset_version}/{file_path:path}")
def get_h5p_asset_file(
    asset_id: int,
    asset_version: int,
    file_path: str | None = None,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    assert_h5p_asset(asset.filename, asset.mime_type)
    if asset_version < 1 or asset_version > (asset.asset_version or 1):
        raise HTTPException(status_code=404, detail="H5P asset version not found")
    if not _has_h5p_playback_access(
        db,
        current_user=current_user,
        asset_id=asset.id,
        asset_version=asset_version,
    ):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    stored_name = asset.object_key.split("/")[-1]
    org_dir = _uploads_root() / str(current_user.org_id)
    extract_dir = resolve_h5p_extract_dir(
        org_dir,
        asset_id=asset.id,
        asset_version=asset_version,
        current_stored_name=stored_name,
        current_asset_version=asset.asset_version or 1,
    )
    return FileResponse(safe_h5p_file_path(extract_dir, file_path))


@player_router.get("/h5p/{asset_id}")
@player_router.get("/h5p/{asset_id}/{file_path:path}")
def get_current_h5p_asset_file(
    asset_id: int,
    file_path: str | None = None,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return get_h5p_asset_file(
        asset_id,
        asset.asset_version or 1,
        file_path,
        db,
        current_user,
    )

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
