from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.auth import TokenData, get_current_user, require_admin
from app.db.engine import apply_tenant_context, db_session
from app.models.course_module import CourseModule
from app.models.media_asset import MediaAsset
from app.models.progression_rule import ProgressionRule
from app.repositories.builder_repo import BuilderRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.progression_rule_repo import ProgressionRuleRepository
from app.services.r2_client import generate_presigned_download_url
from app.services.validation.engine import ValidationEngine

builder_router = APIRouter(prefix="/authoring", tags=["Builder Gateway"])
logger = logging.getLogger("telite.api.builder")


def _apply_builder_tenant_context(db: Session, current_user: TokenData) -> None:
    if current_user.org_id is None:
        raise HTTPException(status_code=403, detail="Organization context is required")
    apply_tenant_context(db, current_user.org_id)


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
    _apply_builder_tenant_context(db, current_user)
    course_repo = CourseRepository(db)
    builder_repo = BuilderRepository(db)
    
    course = course_repo.get_by_id(course_id)
    if not course or course.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Course not found")
        
    sections = builder_repo.get_sections(course_id, current_user.org_id)
    modules = builder_repo.get_modules(course_id, current_user.org_id)
    
    from app.models.lesson_block import LessonBlock
    block_counts = db.query(LessonBlock.module_id, func.count(LessonBlock.id)).filter(
        LessonBlock.org_id == current_user.org_id,
        LessonBlock.deleted_at.is_(None)
    ).group_by(LessonBlock.module_id).all()
    block_count_map = {module_id: count for module_id, count in block_counts}
    
    sections_list = []
    for section in sections:
        sec_dict = section.to_dict()
        sec_dict["modules"] = []
        for m in modules:
            if m.section_id == section.id or (m.section_id is None and m.section == section.sort_order):
                md = m.to_dict()
                md["block_count"] = block_count_map.get(m.id, 0)
                sec_dict["modules"].append(md)
        # Sort modules within the section by sort_order
        sec_dict["modules"].sort(key=lambda m: m["sort_order"])
        sections_list.append(sec_dict)

    assigned_module_ids = {
        module["id"]
        for section in sections_list
        for module in section.get("modules", [])
    }
    unassigned_modules = []
    for m in modules:
        if m.id not in assigned_module_ids:
            md = m.to_dict()
            md["block_count"] = block_count_map.get(m.id, 0)
            unassigned_modules.append(md)
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


@builder_router.get("/courses/{course_id}/validate", dependencies=[Depends(require_admin)])
def validate_course_for_publishing(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    _apply_builder_tenant_context(db, current_user)
    result = ValidationEngine(db).run(course_id, current_user.org_id)
    return result.model_dump()


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
    logger.info("Acquiring builder lock for course_id=%s, user_id=%s, org_id=%s", course_id, current_user.id, current_user.org_id)

    try:
        _apply_builder_tenant_context(db, current_user)
        course_repo = CourseRepository(db)
        builder_repo = BuilderRepository(db)

        logger.debug("Fetching course by id: %s", course_id)
        course = course_repo.get_by_id(course_id)
        logger.debug("Course fetch result: %s", course)

        if not course:
            logger.error("Course not found with id=%s", course_id)
            raise HTTPException(status_code=404, detail="Course not found")

        if course.org_id != current_user.org_id:
            logger.error("Course org_id=%s does not match user org_id=%s", course.org_id, current_user.org_id)
            raise HTTPException(status_code=404, detail="Course not found")

        now = datetime.now(timezone.utc)
        logger.debug("Fetching existing lock for course_id=%s", course_id)
        lock = builder_repo.get_lock(course_id)
        logger.debug("Existing lock: %s", lock)

        if lock and _as_aware_utc(lock.expires_at) > now and lock.user_id != current_user.id:
            logger.warning("Course locked by another user: %s", lock.user_id)
            raise HTTPException(
                status_code=409,
                detail=f"Course is currently locked by user {lock.user_id}."
            )

        expires_at = now + timedelta(minutes=LOCK_DURATION_MINUTES)
        logger.debug("Acquiring lock with expires_at=%s", expires_at)
        lock = builder_repo.acquire_lock(course_id, current_user.id, current_user.org_id, expires_at)
        logger.debug("Lock acquired: %s", lock)

        logger.debug("Logging activity for course_id=%s", course_id)
        builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BUILDER_LOCK_ACQUIRED")

        logger.debug("Committing transaction")
        db.commit()
        logger.info("Lock acquired successfully for course_id=%s", course_id)
        return {"success": True, "expires_at": lock.expires_at.isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error acquiring lock for course_id=%s", course_id)
        raise

@builder_router.post("/courses/{course_id}/heartbeat", dependencies=[Depends(require_admin)])
def renew_builder_lock(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    _apply_builder_tenant_context(db, current_user)
    now = datetime.now(timezone.utc)
    
    # Use atomic UPDATE to prevent race conditions and StaleDataError
    from app.models.course_edit_lock import CourseEditLock
    from sqlalchemy import update
    
    stmt = (
        update(CourseEditLock)
        .where(CourseEditLock.course_id == course_id)
        .where(CourseEditLock.user_id == current_user.id)
        .values(expires_at=now + timedelta(minutes=LOCK_DURATION_MINUTES))
    )
    result = db.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=403, detail="You do not hold the lock for this course.")
    
    db.commit()
    
    # Fetch updated lock to return fresh expires_at
    from app.repositories.builder_repo import BuilderRepository
    builder_repo = BuilderRepository(db)
    lock = builder_repo.get_lock(course_id)
    
    return {"success": True, "expires_at": lock.expires_at.isoformat()}

@builder_router.delete("/courses/{course_id}/lock", dependencies=[Depends(require_admin)])
def release_builder_lock(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    _apply_builder_tenant_context(db, current_user)
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

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ModuleStructureUpdate(BaseModel):
    module_id: int
    sort_order: int

class SectionStructureUpdate(BaseModel):
    section_id: int
    modules: List[ModuleStructureUpdate]

class SaveStructureRequest(BaseModel):
    updates: List[SectionStructureUpdate]

@builder_router.put("/courses/{course_id}/structure", dependencies=[Depends(require_admin)])
def save_course_structure(
    course_id: str,
    request: SaveStructureRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    _apply_builder_tenant_context(db, current_user)
    course_repo = CourseRepository(db)
    course = course_repo.get_by_id(course_id)
    if not course or course.org_id != current_user.org_id:
        raise HTTPException(status_code=404, detail="Course not found")

    for section_update in request.updates:
        section_id = None if section_update.section_id == 0 else section_update.section_id
        for module_update in section_update.modules:
            module = db.query(CourseModule).filter(
                CourseModule.id == module_update.module_id,
                CourseModule.course_id == course_id,
                CourseModule.org_id == current_user.org_id,
            ).first()
            if module:
                module.section_id = section_id
                module.sort_order = module_update.sort_order

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
    _apply_builder_tenant_context(db, current_user)
    builder_repo = BuilderRepository(db)
    blocks = builder_repo.get_blocks(module_id, current_user.org_id)
    results = []
    for b in blocks:
        results.append(_block_to_response(b, db, current_user.org_id))
    return {"blocks": results}

@builder_router.put("/courses/{course_id}/blocks", dependencies=[Depends(require_admin)])
def save_module_blocks(
    course_id: str,
    request: SaveBlocksRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    _apply_builder_tenant_context(db, current_user)
    builder_repo = BuilderRepository(db)
    
    # 1. Check lock
    lock = builder_repo.get_lock(course_id)
    if not lock or lock.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not hold the lock for this course.")

    import json

    from app.models.lesson_block import LessonBlock

    results = []
    
    for bp in request.blocks:
        if bp.block_type == "quiz":
            if not isinstance(bp.settings.get("questions"), list):
                raise HTTPException(status_code=400, detail=f"Quiz block {bp.id or 'new'} must have a 'questions' list in settings")
            for q in bp.settings["questions"]:
                if q.get("type") == "bank_reference":
                    if "question_id" not in q:
                        raise HTTPException(status_code=400, detail="Each bank referenced question must have a question_id")
                    if "question_version_id" not in q:
                        if "version_id" in q:
                            q["question_version_id"] = q["version_id"]
                        else:
                            raise HTTPException(status_code=400, detail="Each bank referenced question must have a question_version_id or version_id")
                elif "question_version_id" not in q and "version_id" in q:
                    q["question_version_id"] = q["version_id"]

        media_asset_id = bp.media_asset_id or bp.settings.get("asset_id")
        if bp.is_deleted and bp.id:
            block = builder_repo.get_block_by_id(bp.id, current_user.org_id)
            if block:
                builder_repo.delete_block(block)
                builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_DELETED", json.dumps({"block_id": bp.id}))
            else:
                raise HTTPException(status_code=404, detail=f"Block {bp.id} not found")
        elif bp.id:
            # Update existing
            block = builder_repo.get_block_by_id(bp.id, current_user.org_id)
            if not block:
                raise HTTPException(status_code=404, detail=f"Block {bp.id} not found")
            block.block_type = bp.block_type
            block.content = bp.content
            block.media_asset_id = media_asset_id
            block.metadata_json = bp.settings
            block.sort_order = bp.sort_order
            builder_repo.save_block(block)
            builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_UPDATED", json.dumps({"block_id": block.id, "type": block.block_type}))
            
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
            builder_repo.log_activity(course_id, current_user.id, current_user.org_id, "BLOCK_CREATED", json.dumps({"block_id": block.id, "type": block.block_type}))
            
            results.append(_block_to_response(block, db, current_user.org_id))

    db.commit()
    return {"success": True, "blocks": results}


# -----------------------------------------------------------------------------
# 4. Progression Rules Management
# -----------------------------------------------------------------------------

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CreateProgressionRuleRequest(BaseModel):
    target_type: str
    target_id: int
    rule_type: str
    rule_value: Dict[str, Any] = {}


class UpdateProgressionRuleRequest(BaseModel):
    rule_type: Optional[str] = None
    rule_value: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


@builder_router.get("/courses/{course_id}/progression-rules")
def get_progression_rules(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all progression rules for a course."""
    _apply_builder_tenant_context(db, current_user)
    rule_repo = ProgressionRuleRepository(db)
    
    # Get all modules and sections for the course
    modules = db.query(CourseModule).filter(
        CourseModule.course_id == course_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).all()
    
    from app.models.course_section import CourseSection
    sections = db.query(CourseSection).filter(
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).all()
    
    # Get rules for each target
    all_rules = []
    for module in modules:
        rules = rule_repo.get_rules_for_target("module", module.id, current_user.org_id)
        all_rules.extend([r.to_dict() for r in rules])
    
    for section in sections:
        rules = rule_repo.get_rules_for_target("section", section.id, current_user.org_id)
        all_rules.extend([r.to_dict() for r in rules])
    
    return {"rules": all_rules}


@builder_router.post("/courses/{course_id}/progression-rules", dependencies=[Depends(require_admin)])
def create_progression_rule(
    course_id: str,
    req: CreateProgressionRuleRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new progression rule for a module or section."""
    _apply_builder_tenant_context(db, current_user)
    rule_repo = ProgressionRuleRepository(db)
    
    # Validate target exists and belongs to course
    if req.target_type == "module":
        module = db.query(CourseModule).filter(
            CourseModule.id == req.target_id,
            CourseModule.course_id == course_id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).first()
        if not module:
            raise HTTPException(status_code=404, detail="Module not found")
    elif req.target_type == "section":
        from app.models.course_section import CourseSection
        section = db.query(CourseSection).filter(
            CourseSection.id == req.target_id,
            CourseSection.course_id == course_id,
            CourseSection.org_id == current_user.org_id,
            CourseSection.deleted_at.is_(None),
        ).first()
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid target_type. Must be 'module' or 'section'")
    
    rule = rule_repo.create_rule(
        target_type=req.target_type,
        target_id=req.target_id,
        rule_type=req.rule_type,
        rule_value=req.rule_value,
        org_id=current_user.org_id,
        created_by=current_user.id,
    )
    
    db.commit()
    return {"success": True, "rule": rule.to_dict()}


@builder_router.put("/progression-rules/{rule_id}", dependencies=[Depends(require_admin)])
def update_progression_rule(
    rule_id: int,
    req: UpdateProgressionRuleRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Update an existing progression rule."""
    _apply_builder_tenant_context(db, current_user)
    rule_repo = ProgressionRuleRepository(db)
    
    rule = db.query(ProgressionRule).filter(
        ProgressionRule.id == rule_id,
        ProgressionRule.org_id == current_user.org_id,
        ProgressionRule.deleted_at.is_(None),
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    updated_rule = rule_repo.update_rule(
        rule,
        rule_type=req.rule_type,
        rule_value=req.rule_value,
        is_active=req.is_active,
        updated_by=current_user.id,
    )
    
    db.commit()
    return {"success": True, "rule": updated_rule.to_dict()}


@builder_router.delete("/progression-rules/{rule_id}")
def delete_progression_rule(
    rule_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a progression rule (soft delete)."""
    _apply_builder_tenant_context(db, current_user)
    rule_repo = ProgressionRuleRepository(db)
    
    rule = db.query(ProgressionRule).filter(
        ProgressionRule.id == rule_id,
        ProgressionRule.org_id == current_user.org_id,
        ProgressionRule.deleted_at.is_(None),
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule_repo.delete_rule(rule)
    db.commit()
    
    return {"success": True}
