from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_admin, TokenData
from app.core.permissions import require_capability
from app.db.engine import db_session
from app.repositories.course_repo import CourseRepository
from app.repositories.builder_repo import BuilderRepository
from app.models.course_module import CourseModule
from app.models.media_asset import MediaAsset
from app.services.r2_client import generate_presigned_download_url
from app.services.audit_service import AuditService

builder_router = APIRouter(prefix="/authoring", tags=["Builder Gateway"])


def _download_url_for_asset(asset: MediaAsset) -> str:
    if asset.object_key.startswith("/uploads/"):
        return asset.object_key
    return generate_presigned_download_url(asset.object_key)


def _block_to_response(block, db: Session, org_id: int) -> dict:
    block_dict = block.to_dict()
    settings = block_dict.pop("metadata_json", {}) or {}
    if block.media_asset_id:
        settings.setdefault("asset_id", block.media_asset_id)
        asset = db.query(MediaAsset).filter(
            MediaAsset.id == block.media_asset_id,
            MediaAsset.org_id == org_id,
            MediaAsset.deleted_at.is_(None),
        ).first()
        if asset:
            settings.setdefault("url", _download_url_for_asset(asset))
            settings.setdefault("filename", asset.filename)
            settings.setdefault("mime_type", asset.mime_type)
            settings.setdefault("asset_version", asset.asset_version)
    block_dict["settings"] = settings
    return block_dict

# -----------------------------------------------------------------------------
# 1. Builder Structure Fetch
# -----------------------------------------------------------------------------

@builder_router.get("/courses/{course_id}/builder", dependencies=[Depends(require_admin)])
def get_builder_structure(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course_repo = CourseRepository(db)
    builder_repo = BuilderRepository(db)
    
    course = course_repo.get_by_id(course_id)
    if not course or course.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Course not found")
        
    sections = builder_repo.get_sections(course_id, current_user.org_id)
    modules = builder_repo.get_modules(course_id, current_user.org_id)
    
    sections_list = []
    for section in sections:
        sec_dict = section.to_dict()
        sec_dict["modules"] = [
            m.to_dict()
            for m in modules
            if m.section_id == section.id or (m.section_id is None and m.section == section.sort_order)
        ]
        sections_list.append(sec_dict)

    assigned_module_ids = {
        module["id"]
        for section in sections_list
        for module in section.get("modules", [])
    }
    unassigned_modules = [m.to_dict() for m in modules if m.id not in assigned_module_ids]
    if unassigned_modules:
        sections_list.append({
            "id": 0,
            "course_id": course_id,
            "org_id": current_user.org_id,
            "title": "Course modules",
            "sort_order": -1,
            "deleted_at": None,
            "deleted_by": None,
            "modules": unassigned_modules,
        })
        
    return {
        "course": course.to_dict(),
        "sections": sections_list
    }

# -----------------------------------------------------------------------------
# 2. Builder Lock Service
# -----------------------------------------------------------------------------

LOCK_DURATION_MINUTES = 15

def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

@builder_router.post("/courses/{course_id}/lock", dependencies=[Depends(require_admin)])
def acquire_builder_lock(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course_repo = CourseRepository(db)
    builder_repo = BuilderRepository(db)
    
    course = course_repo.get_by_id(course_id)
    if not course or course.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Course not found")

    now = datetime.now(timezone.utc)
    lock = builder_repo.get_lock(course_id)
    
    if lock and _as_aware_utc(lock.expires_at) > now and lock.user_id != current_user.id:
        raise HTTPException(
            status_code=409, 
            detail=f"Course is currently locked by user {lock.user_id}."
        )
        
    expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)
    lock = builder_repo.acquire_lock(course_id, current_user.id, current_user.org_id, expires_at)
    builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BUILDER_LOCK_ACQUIRED")
    
    db.commit()
    return {"success": True, "expires_at": lock.expires_at.isoformat()}

@builder_router.post("/courses/{course_id}/heartbeat", dependencies=[Depends(require_admin)])
def renew_builder_lock(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    builder_repo = BuilderRepository(db)
    now = datetime.now(timezone.utc)
    lock = builder_repo.get_lock(course_id)
    
    if not lock or lock.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not hold the lock for this course.")
        
    lock.expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)
    db.commit()
    return {"success": True, "expires_at": lock.expires_at.isoformat()}

@builder_router.delete("/courses/{course_id}/lock", dependencies=[Depends(require_admin)])
def release_builder_lock(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    builder_repo = BuilderRepository(db)
    lock = builder_repo.get_lock(course_id)
    
    if lock:
        if lock.user_id == current_user.id:
            builder_repo.release_lock(lock)
            builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BUILDER_LOCK_RELEASED")
            db.commit()
            return {"success": True}
        else:
            raise HTTPException(status_code=403, detail="You do not hold the lock for this course.")
            
    return {"success": True}

# -----------------------------------------------------------------------------
# 3. Block Management & Autosave
# -----------------------------------------------------------------------------

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ModuleStructureUpdate(BaseModel):
    module_id: int
    sort_order: int

class SectionStructureUpdate(BaseModel):
    section_id: int
    sort_order: Optional[int] = None
    modules: List[ModuleStructureUpdate]

class SaveStructureRequest(BaseModel):
    updates: List[SectionStructureUpdate]

@builder_router.put("/courses/{course_id}/structure", dependencies=[Depends(require_admin), Depends(require_capability("module.edit"))])
def save_course_structure(
    course_id: str,
    request: SaveStructureRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course or course.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Course not found")

    for section_update in request.updates:
        section_id = None if section_update.section_id == 0 else section_update.section_id
        
        if section_id is not None and section_update.sort_order is not None:
            from app.models.course_section import CourseSection
            sec = db.query(CourseSection).filter(
                CourseSection.id == section_id,
                CourseSection.course_id == course_id,
                CourseSection.org_id == current_user.org_id
            ).first()
            if sec:
                sec.sort_order = section_update.sort_order
                AuditService.log(db, current_user.org_id, current_user.id, "section", sec.id, "update", course_id)
                
        for module_update in section_update.modules:
            module = db.query(CourseModule).filter(
                CourseModule.id == module_update.module_id,
                CourseModule.course_id == course_id,
                CourseModule.org_id == current_user.org_id,
            ).first()
            if module:
                module.section_id = section_id
                module.sort_order = module_update.sort_order
                AuditService.log(db, current_user.org_id, current_user.id, "module", module.id, "update", course_id)

    db.commit()
    return {"success": True}

class BlockPayload(BaseModel):
    id: Optional[int] = None
    module_id: int
    block_type: str
    content: str
    media_asset_id: Optional[int] = None
    settings: Dict[str, Any] = {}
    sort_order: int
    is_deleted: bool = False

class SaveBlocksRequest(BaseModel):
    blocks: List[BlockPayload]

@builder_router.get("/courses/{course_id}/modules/{module_id}/blocks", dependencies=[Depends(require_admin)])
def get_module_blocks(
    course_id: str,
    module_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    builder_repo = BuilderRepository(db)
    blocks = builder_repo.get_blocks(module_id, current_user.org_id)
    results = []
    for b in blocks:
        results.append(_block_to_response(b, db, current_user.org_id))
    return {"blocks": results}

@builder_router.put("/courses/{course_id}/blocks", dependencies=[Depends(require_admin), Depends(require_capability("block.edit"))])
def save_module_blocks(
    course_id: str,
    request: SaveBlocksRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    builder_repo = BuilderRepository(db)
    
    # 1. Check lock
    lock = builder_repo.get_lock(course_id)
    if not lock or lock.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not hold the lock for this course.")

    from app.models.lesson_block import LessonBlock
    import json

    results = []
    
    for bp in request.blocks:
        media_asset_id = bp.media_asset_id or bp.settings.get("asset_id")
        if bp.is_deleted and bp.id:
            block = builder_repo.get_block_by_id(bp.id, current_user.org_id)
            if block:
                before_dict = block.to_dict()
                builder_repo.delete_block(block, current_user.id)
                builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_DELETED", json.dumps({"block_id": bp.id}))
                AuditService.log(db, current_user.org_id, current_user.id, "Block", bp.id, "delete", course_id, before_dict=before_dict)
        elif bp.id:
            # Update existing
            block = builder_repo.get_block_by_id(bp.id, current_user.org_id)
            if block:
                before_dict = block.to_dict()
                # Basic optimistic concurrency could go here by checking a version number if it existed
                block.block_type = bp.block_type
                block.content = bp.content
                block.media_asset_id = media_asset_id
                block.metadata_json = bp.settings
                block.sort_order = bp.sort_order
                builder_repo.save_block(block)
                after_dict = block.to_dict()
                builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_UPDATED", json.dumps({"block_id": block.id, "type": block.block_type}))
                AuditService.log(db, current_user.org_id, current_user.id, "Block", block.id, "update", course_id, before_dict=before_dict, after_dict=after_dict)
                
                results.append(_block_to_response(block, db, current_user.org_id))
        else:
            # Create new
            block = LessonBlock(
                module_id=bp.module_id,
                org_id=current_user.org_id,
                block_type=bp.block_type,
                content=bp.content,
                media_asset_id=media_asset_id,
                metadata_json=bp.settings,
                sort_order=bp.sort_order
            )
            builder_repo.save_block(block)
            after_dict = block.to_dict()
            builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_CREATED", json.dumps({"block_id": block.id, "type": block.block_type}))
            AuditService.log(db, current_user.org_id, current_user.id, "Block", block.id, "create", course_id, after_dict=after_dict)
            
            results.append(_block_to_response(block, db, current_user.org_id))

    db.commit()
    return {"success": True, "blocks": results}

@builder_router.get("/courses/{course_id}/validate", dependencies=[Depends(require_admin)])
def validate_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    from app.services.validation.engine import ValidationEngine
    val_engine = ValidationEngine(db)
    result = val_engine.run(course_id, current_user.org_id)
    return result.dict()

@builder_router.get("/courses/{course_id}/audit-logs", dependencies=[Depends(require_admin)])
def get_audit_logs(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    from app.models.audit_log import AuditLog
    logs = db.query(AuditLog).filter(
        AuditLog.course_id == course_id,
        AuditLog.org_id == current_user.org_id
    ).order_by(AuditLog.created_at.desc()).all()
    
    return {"audit_logs": [log.to_dict() for log in logs]}
