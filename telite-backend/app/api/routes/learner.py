"""Learner API Endpoints."""

import copy
from typing import List, Optional
from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_admin, TokenData
from app.core.storage_paths import media_upload_root
from app.db.engine import db_session
from app.repositories.learner_repo import LearnerRepository
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.completion_policy_service import CompletionPolicyService
from app.services.gradebook_service import GradebookService
from app.services.learning_path_unlock_service import LearningPathUnlockService
from app.services.progression_rule_engine import ProgressionRuleEngine
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.course import Course
from app.models.module_progress import ModuleProgress
from app.models.section_progress import SectionProgress
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.learning_session import LearningSession
from app.models.user import User
from app.services.pal_score_service import PALScoreService

learner_router = APIRouter(prefix="/learner", tags=["Learner APIs"])


def _sanitize_quiz_settings(settings: dict | None) -> dict:
    """Return learner-safe native quiz metadata without answer keys."""
    safe = copy.deepcopy(settings or {})
    questions = []
    for question in safe.get("questions", []) or []:
        sanitized = {
            key: value
            for key, value in question.items()
            if key not in {"correct_option_id", "correct_answer", "explanation"}
        }
        questions.append(sanitized)
    safe["questions"] = questions
    return safe


def _sanitize_block_for_learner(block: dict) -> dict:
    safe_block = copy.deepcopy(block)
    block_type = safe_block.get("block_type")
    settings = safe_block.get("metadata_json") or safe_block.get("settings") or {}
    if block_type in ("quiz", "native_quiz"):
        settings = _sanitize_quiz_settings(settings)
    safe_block["settings"] = settings
    safe_block["metadata_json"] = settings
    return safe_block

class CourseListResponse(BaseModel):
    id: str
    name: str
    description: str
    slug: str
    status: str
    enrolled_count: int
    completion_rate: float
    modules_count: int
    tier: str

class ModuleProgressUpdate(BaseModel):
    module_id: int
    status: str
    last_block_id: Optional[str] = None
    video_position_seconds: Optional[int] = None

class ProgressMutationRequest(BaseModel):
    course_id: str
    module_updates: List[ModuleProgressUpdate]

class LearnerEventPayload(BaseModel):
    event_type: str
    course_id: Optional[str] = None
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    payload_json: dict = {}

class LearnerEventsBatchRequest(BaseModel):
    events: List[LearnerEventPayload]

class HeartbeatRequest(BaseModel):
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    time_spent_seconds: int

class LearningSessionStartRequest(BaseModel):
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None

class LearningSessionHeartbeatRequest(BaseModel):
    session_id: int
    course_id: str
    module_id: Optional[int] = None
    block_id: Optional[int] = None
    active_seconds: int

class LearningSessionEndRequest(BaseModel):
    session_id: int
    reason: Optional[str] = "ended"

class AccessValidationRequest(BaseModel):
    target_type: str
    target_id: int

@learner_router.get("/courses", response_model=List[CourseListResponse])
def get_learner_courses(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve courses available/enrolled for the learner."""
    learner_repo = LearnerRepository(db)
    courses = learner_repo.get_enrolled_courses(current_user.id, current_user.org_id)
    return [
        CourseListResponse(
            id=c.id, name=c.name, description=c.description, slug=c.slug,
            status=c.status, enrolled_count=c.enrolled_count, 
            completion_rate=c.completion_rate, modules_count=c.module_count,
            tier=c.tier
        ) for c in courses
    ]

@learner_router.get("/paths")
def get_learner_paths(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve learning paths available/enrolled for the learner."""
    learner_repo = LearnerRepository(db)
    paths = learner_repo.get_learning_paths(current_user.id, current_user.org_id)
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description
        } for p in paths
    ]

@learner_router.get("/paths/{id}")
def get_learner_path(
    id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve details for a specific learning path."""
    learner_repo = LearnerRepository(db)
    path = learner_repo.get_learning_path(id, current_user.id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    return {
        "id": path.id,
        "title": path.title,
        "description": path.description,
        "settings": path.settings
    }

@learner_router.get("/courses/{id}")
def get_learner_course(
    id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve details for a specific course, gated by enrollment access.
    Serves snapshot-frozen content when learner has an enrolled_version.
    Returns sections ordered by sort_order ASC, modules ordered by sort_order ASC within sections."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    learner_repo = LearnerRepository(db)
    course = learner_repo.get_course(id, current_user.id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if learner is pinned to a specific version
    from app.models.course_version import CourseVersion
    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, id, current_user.org_id)
    enrolled_version = cp.enrolled_version if cp else None

    if enrolled_version:
        # Serve from frozen snapshot
        version = db.query(CourseVersion).filter(
            CourseVersion.course_id == id,
            CourseVersion.version_number == enrolled_version,
        ).first()
        if version and version.snapshot_json:
            snapshot = version.snapshot_json
            snapshot_sections = []
            # Sort sections by sort_order
            sorted_sections = sorted(snapshot.get("sections", []), key=lambda s: s.get("sort_order", 0))
            for section in sorted_sections:
                section_modules = []
                # Sort modules within section by sort_order
                sorted_modules = sorted(section.get("modules", []), key=lambda m: m.get("sort_order", 0))
                for mod in sorted_modules:
                    blocks = mod.get("blocks", [])
                    for idx, b in enumerate(blocks):
                        blocks[idx] = _sanitize_block_for_learner(b)
                    section_modules.append({
                        "id": mod["id"],
                        "title": mod.get("title", ""),
                        "module_type": mod.get("module_type", "page"),
                        "sort_order": mod.get("sort_order", 0),
                        "section_id": mod.get("section_id"),
                        "status": mod.get("status", "published"),
                        "content_url": mod.get("content_url"),
                        "content": blocks,
                    })
                snapshot_sections.append({
                    "id": section.get("id"),
                    "course_id": section.get("course_id"),
                    "org_id": section.get("org_id"),
                    "title": section.get("title", ""),
                    "sort_order": section.get("sort_order", 0),
                    "deleted_at": section.get("deleted_at"),
                    "deleted_by": section.get("deleted_by"),
                    "modules": section_modules,
                })
            return {
                "id": course.id,
                "name": snapshot.get("course", {}).get("name", course.name),
                "description": course.description,
                "sections": snapshot_sections,
                "version": enrolled_version,
            }

    # Fallback: serve live draft content
    sections = db.query(CourseSection).filter(
        CourseSection.course_id == course.id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).order_by(CourseSection.sort_order.asc()).all()
    
    modules = db.query(CourseModule).filter(
        CourseModule.course_id == course.id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).order_by(CourseModule.sort_order.asc()).all()

    blocks_by_module = {}
    if modules:
        module_ids = [module.id for module in modules]
        blocks = db.query(LessonBlock).filter(
            LessonBlock.module_id.in_(module_ids),
            LessonBlock.org_id == current_user.org_id,
            LessonBlock.deleted_at.is_(None),
        ).order_by(LessonBlock.sort_order.asc()).all()
        for block in blocks:
            block_dict = block.to_dict()
            block_dict["settings"] = block_dict.pop("metadata_json", {})
            block_dict = _sanitize_block_for_learner(block_dict)
            blocks_by_module.setdefault(block.module_id, []).append(block_dict)

    # Group modules by sections
    sections_list = []
    for section in sections:
        sec_dict = section.to_dict()
        sec_dict["modules"] = []
        # Get modules for this section, ordered by sort_order
        section_modules = [m for m in modules if m.section_id == section.id]
        section_modules.sort(key=lambda m: m.sort_order)
        
        for module in section_modules:
            module_dict = module.to_dict()
            module_dict["content"] = blocks_by_module.get(module.id, [])
            sec_dict["modules"].append(module_dict)
        sections_list.append(sec_dict)
    
    # Handle unassigned modules (modules without sections)
    assigned_module_ids = {
        module.get("id")
        for section in sections_list
        for module in section.get("modules", [])
    }
    unassigned_modules = [m for m in modules if m.id not in assigned_module_ids]
    unassigned_modules.sort(key=lambda m: m.sort_order)
    
    if unassigned_modules:
        sections_list.append({
            "id": 0,
            "course_id": course.id,
            "org_id": current_user.org_id,
            "title": "Course modules",
            "sort_order": -1,
            "deleted_at": None,
            "deleted_by": None,
            "modules": [m.to_dict() for m in unassigned_modules],
        })
    
    # Flatten modules for easier frontend consumption
    modules_json = []
    for section in sections_list:
        for module in section.get("modules", []):
            modules_json.append(module)
    
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "sections": sections_list,
        "modules_json": modules_json,
        "progress": cp.to_dict() if cp else None,
    }

@learner_router.get("/modules/{id}")
def get_learner_module(
    id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve module data. Assuming module ID maps to course access."""
    # To secure this properly, we need the course_id for the module to check EnrollmentRepository.
    # In a full impl, we'd fetch the module, then check enrollment on module.course_id.
    from app.models.course_module import CourseModule
    module = db.query(CourseModule).filter_by(id=id, org_id=current_user.org_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, module.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")
    
    # Check progression rules
    engine = ProgressionRuleEngine(db)
    access_result = engine.validate_access(
        user_id=current_user.id,
        target_type="module",
        target_id=id,
        org_id=current_user.org_id
    )
    if not access_result.allowed:
        raise HTTPException(status_code=403, detail=access_result.reason or "Access denied by progression rules")
        
    return {
        "id": module.id,
        "title": module.title,
        "module_type": module.module_type,
        "content_url": module.content_url,
    }

@learner_router.post("/progress")
def update_progress(
    req: ProgressMutationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Update learner progress for course, sections, and modules.
    Updates section progress based on module completion within each section."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, req.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    progress_repo = ProgressRepository(db)
    
    # Write event log
    event = LearnerEvent(
        user_id=current_user.id,
        course_id=req.course_id,
        event_type="PROGRESS_MUTATION",
        schema_version="1.0",
        payload_json=req.dict(),
        created_at=datetime.utcnow(),
        org_id=current_user.org_id
    )
    db.add(event)

    course_progress = progress_repo.get_course_progress(current_user.id, req.course_id, current_user.org_id)
    if not course_progress:
        course_progress = CourseProgress(
            user_id=current_user.id, course_id=req.course_id, org_id=current_user.org_id,
            status="in_progress", completion_percentage=0.0, started_at=datetime.utcnow()
        )
    
    for mod_upd in req.module_updates:
        mp = progress_repo.get_module_progress(current_user.id, mod_upd.module_id, current_user.org_id)
        if not mp:
            mp = ModuleProgress(
                user_id=current_user.id, module_id=mod_upd.module_id, org_id=current_user.org_id,
                status=mod_upd.status, started_at=datetime.utcnow()
            )
        else:
            mp.status = mod_upd.status
            
        if mod_upd.last_block_id:
            mp.last_block_id = mod_upd.last_block_id
            
        if mod_upd.status == "completed" and not mp.completed_at:
            mp.completed_at = datetime.utcnow()
            # Emit MODULE_COMPLETED event
            db.add(LearnerEvent(
                user_id=current_user.id,
                course_id=req.course_id,
                module_id=mod_upd.module_id,
                event_type="MODULE_COMPLETED",
                schema_version="1.0",
                payload_json={},
                created_at=datetime.utcnow(),
                org_id=current_user.org_id
            ))
            
        progress_repo.upsert_module_progress(mp)

    # Update section progress based on module completion
    # Get all sections for this course
    sections = db.query(CourseSection).filter(
        CourseSection.course_id == req.course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).order_by(CourseSection.sort_order.asc()).all()
    
    for section in sections:
        # Get all modules in this section
        section_modules = db.query(CourseModule).filter(
            CourseModule.section_id == section.id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).all()
        
        if not section_modules:
            continue
        
        # Count completed modules in this section
        completed_in_section = 0
        for module in section_modules:
            mp = progress_repo.get_module_progress(current_user.id, module.id, current_user.org_id)
            if mp and mp.status == "completed":
                completed_in_section += 1
        
        # Update section progress
        sp = progress_repo.get_section_progress(current_user.id, section.id, current_user.org_id)
        section_completion_pct = (completed_in_section / len(section_modules) * 100.0) if section_modules else 0.0
        
        if not sp:
            sp = SectionProgress(
                user_id=current_user.id,
                section_id=section.id,
                org_id=current_user.org_id,
                status="in_progress" if completed_in_section > 0 else "not_started",
                completion_percentage=section_completion_pct,
                started_at=datetime.utcnow() if completed_in_section > 0 else None
            )
        else:
            sp.completion_percentage = section_completion_pct
            if completed_in_section > 0 and sp.status == "not_started":
                sp.status = "in_progress"
                sp.started_at = sp.started_at or datetime.utcnow()
        
        # Mark section as completed if all modules are completed
        if completed_in_section == len(section_modules) and sp.status != "completed":
            sp.status = "completed"
            sp.completed_at = datetime.utcnow()
            # Emit SECTION_COMPLETED event
            db.add(LearnerEvent(
                user_id=current_user.id,
                course_id=req.course_id,
                event_type="SECTION_COMPLETED",
                schema_version="1.0",
                payload_json={"section_id": section.id, "section_title": section.title},
                created_at=datetime.utcnow(),
                org_id=current_user.org_id
            ))
        
        progress_repo.upsert_section_progress(sp)

    course_module_ids = [
        module_id for (module_id,) in db.query(CourseModule.id).filter(
            CourseModule.course_id == req.course_id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).all()
    ]
    completed_module_ids = {
        module_id for (module_id,) in db.query(ModuleProgress.module_id).filter(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.org_id == current_user.org_id,
            ModuleProgress.module_id.in_(course_module_ids),
            ModuleProgress.status == "completed",
        ).all()
    }
    total_modules = len(course_module_ids)
    completed_count = len(completed_module_ids)
    completion_percentage = (completed_count / total_modules * 100.0) if total_modules else 0.0
    course_progress.completion_percentage = completion_percentage

    # Only auto-complete if NOT using explicit submission workflow
    # Check if course has been explicitly submitted
    if course_progress.status != "submitted":
        if not total_modules or completed_count != total_modules:
            course_progress.status = "in_progress"
            course_progress.completed_at = None
        # Note: We don't auto-set to "completed" anymore - that requires explicit submission

    evaluation = CompletionPolicyService(db).evaluate_course_completion(
        user_id=current_user.id,
        course_id=req.course_id,
        org_id=current_user.org_id,
        course_progress=course_progress,
    )
    if evaluation.completed_now:
        # Emit COURSE_COMPLETED only when policy-driven academic completion transitions.
        db.add(LearnerEvent(
            user_id=current_user.id,
            course_id=req.course_id,
            event_type="COURSE_COMPLETED",
            schema_version="1.0",
            payload_json=evaluation.to_event_payload(),
            created_at=datetime.utcnow(),
            org_id=current_user.org_id
        ))

    progress_repo.upsert_course_progress(course_progress)
    PALScoreService(db).recompute_user(current_user.id, current_user.org_id)
    db.commit()

    if evaluation.completed_now:
        from app.models.learning_path import LearningPathCourse
        unlock_svc = LearningPathUnlockService(db)
        
        path_courses = db.query(LearningPathCourse).filter_by(course_id=req.course_id).all()
        for pc in path_courses:
            # We evaluate unlocks for every path this course belongs to
            # This handles LearningPathUnlockService executing after course completion events
            unlock_svc.evaluate_unlocks(current_user.id, pc.path_id, current_user.org_id)

    return {"status": "success", "course_status": course_progress.status}

@learner_router.post("/heartbeat")
def heartbeat(
    req: HeartbeatRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Record offline heartbeat and time spent."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, req.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    now = datetime.utcnow()

    # Record event
    event = LearnerEvent(
        user_id=current_user.id,
        course_id=req.course_id,
        module_id=req.module_id,
        block_id=req.block_id,
        event_type="HEARTBEAT",
        schema_version="1.0",
        payload_json={"time_spent_seconds": req.time_spent_seconds},
        created_at=now,
        org_id=current_user.org_id
    )
    db.add(event)

    # Update time spent in course progress
    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, req.course_id, current_user.org_id)
    if not cp:
        cp = CourseProgress(
            user_id=current_user.id,
            course_id=req.course_id,
            org_id=current_user.org_id,
            status="in_progress",
            completion_percentage=0.0,
            time_spent_seconds=0,
            started_at=now,
        )
        db.add(LearnerEvent(
            user_id=current_user.id,
            course_id=req.course_id,
            event_type="COURSE_STARTED",
            schema_version="1.0",
            payload_json={},
            created_at=now,
            org_id=current_user.org_id,
        ))
    elif cp.status == "not_started":
        cp.status = "in_progress"
        cp.started_at = cp.started_at or now

    cp.time_spent_seconds = (cp.time_spent_seconds or 0) + req.time_spent_seconds
    cp.last_viewed_at = now
    progress_repo.upsert_course_progress(cp)

    if req.module_id:
        mp = progress_repo.get_module_progress(current_user.id, req.module_id, current_user.org_id)
        if not mp:
            mp = ModuleProgress(
                user_id=current_user.id,
                module_id=req.module_id,
                org_id=current_user.org_id,
                status="in_progress",
                started_at=now,
            )
        elif mp.status == "not_started":
            mp.status = "in_progress"
            mp.started_at = mp.started_at or now
        mp.time_spent_seconds = (mp.time_spent_seconds or 0) + req.time_spent_seconds
        mp.last_viewed_at = now
        if req.block_id:
            mp.last_block_id = str(req.block_id)
        progress_repo.upsert_module_progress(mp)

    db.commit()
    return {"status": "success"}


def _module_section_id(db: Session, module_id: int | None, org_id: int) -> int | None:
    if not module_id:
        return None
    module = db.query(CourseModule).filter(CourseModule.id == module_id, CourseModule.org_id == org_id).first()
    return module.section_id if module else None


def _apply_active_seconds(
    db: Session,
    *,
    current_user: TokenData,
    course_id: str,
    module_id: int | None,
    block_id: int | None,
    active_seconds: int,
) -> None:
    seconds = max(0, min(int(active_seconds or 0), 90))
    if seconds <= 0:
        return
    now = datetime.now(timezone.utc)
    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, course_id, current_user.org_id)
    if not cp:
        cp = CourseProgress(
            user_id=current_user.id,
            course_id=course_id,
            org_id=current_user.org_id,
            status="in_progress",
            completion_percentage=0.0,
            time_spent_seconds=0,
            started_at=now,
        )
        db.add(LearnerEvent(
            user_id=current_user.id,
            course_id=course_id,
            event_type="COURSE_STARTED",
            schema_version="1.0",
            payload_json={},
            created_at=now,
            org_id=current_user.org_id,
        ))
    elif cp.status == "not_started":
        cp.status = "in_progress"
        cp.started_at = cp.started_at or now
    cp.time_spent_seconds = (cp.time_spent_seconds or 0) + seconds
    cp.last_viewed_at = now
    progress_repo.upsert_course_progress(cp)

    if module_id:
        mp = progress_repo.get_module_progress(current_user.id, module_id, current_user.org_id)
        if not mp:
            mp = ModuleProgress(user_id=current_user.id, module_id=module_id, org_id=current_user.org_id, status="in_progress", started_at=now)
        elif mp.status == "not_started":
            mp.status = "in_progress"
            mp.started_at = mp.started_at or now
        mp.time_spent_seconds = (mp.time_spent_seconds or 0) + seconds
        mp.last_viewed_at = now
        if block_id:
            mp.last_block_id = str(block_id)
        progress_repo.upsert_module_progress(mp)

    if block_id and module_id:
        bp = progress_repo.get_block_progress(current_user.id, block_id, current_user.org_id)
        if not bp:
            bp = LessonBlockProgress(user_id=current_user.id, module_id=module_id, block_id=block_id, org_id=current_user.org_id, status="not_started")
        bp.time_spent_seconds = (bp.time_spent_seconds or 0) + seconds
        bp.last_viewed_at = now
        progress_repo.upsert_block_progress(bp)

    db.add(LearnerEvent(
        user_id=current_user.id,
        course_id=course_id,
        module_id=module_id,
        block_id=block_id,
        event_type="HEARTBEAT",
        schema_version="1.0",
        payload_json={"time_spent_seconds": seconds, "source": "learning_session"},
        created_at=now,
        org_id=current_user.org_id,
    ))


@learner_router.post("/learning-sessions/start")
def start_learning_session(
    req: LearningSessionStartRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    if not EnrollmentRepository(db).has_access(current_user.id, req.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")
    now = datetime.now(timezone.utc)
    session = LearningSession(
        user_id=current_user.id,
        course_id=req.course_id,
        module_id=req.module_id,
        section_id=_module_section_id(db, req.module_id, current_user.org_id),
        block_id=req.block_id,
        org_id=current_user.org_id,
        started_at=now,
        last_heartbeat_at=now,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session": session.to_dict()}


@learner_router.post("/learning-sessions/heartbeat")
def heartbeat_learning_session(
    req: LearningSessionHeartbeatRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    session = db.query(LearningSession).filter(
        LearningSession.id == req.session_id,
        LearningSession.user_id == current_user.id,
        LearningSession.org_id == current_user.org_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Learning session is closed")
    if not EnrollmentRepository(db).has_access(current_user.id, req.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")
    seconds = max(0, min(int(req.active_seconds or 0), 90))
    session.course_id = req.course_id
    session.module_id = req.module_id
    session.section_id = _module_section_id(db, req.module_id, current_user.org_id)
    session.block_id = req.block_id
    session.active_seconds = (session.active_seconds or 0) + seconds
    session.last_heartbeat_at = datetime.now(timezone.utc)
    _apply_active_seconds(
        db,
        current_user=current_user,
        course_id=req.course_id,
        module_id=req.module_id,
        block_id=req.block_id,
        active_seconds=seconds,
    )
    db.commit()
    return {"session": session.to_dict()}


@learner_router.post("/learning-sessions/end")
def end_learning_session(
    req: LearningSessionEndRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    session = db.query(LearningSession).filter(
        LearningSession.id == req.session_id,
        LearningSession.user_id == current_user.id,
        LearningSession.org_id == current_user.org_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Learning session not found")
    if session.status == "active":
        session.status = "ended"
        session.ended_at = datetime.now(timezone.utc)
        session.end_reason = req.reason or "ended"
        db.commit()
    return {"session": session.to_dict()}

@learner_router.post("/events")
def record_events(
    req: LearnerEventsBatchRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Record arbitrary granular events from the frontend (e.g. VIDEO_STARTED)."""
    enrollment_repo = EnrollmentRepository(db)
    events = []
    for ev in req.events:
        if ev.course_id and not enrollment_repo.has_access(current_user.id, ev.course_id, current_user.org_id):
            raise HTTPException(status_code=403, detail="Not enrolled or access denied")

        events.append(LearnerEvent(
            user_id=current_user.id,
            course_id=ev.course_id,
            module_id=ev.module_id,
            block_id=ev.block_id,
            event_type=ev.event_type,
            schema_version="1.0",
            payload_json=ev.payload_json,
            created_at=datetime.utcnow(),
            org_id=current_user.org_id
        ))
    if events:
        db.add_all(events)
        db.commit()
    return {"status": "success", "recorded": len(events)}

@learner_router.post("/validate-access")
def validate_access(
    req: AccessValidationRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Validate whether a learner can access a module or section based on progression rules."""
    engine = ProgressionRuleEngine(db)
    result = engine.validate_access(
        user_id=current_user.id,
        target_type=req.target_type,
        target_id=req.target_id,
        org_id=current_user.org_id
    )
    
    return {
        "allowed": result.allowed,
        "reason": result.reason
    }

@learner_router.get("/courses/{course_id}/module-progress")
def get_module_progress(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all module progress for a course.
    Returns a mapping of module_id -> status for all modules in the course."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    # Get all modules for this course
    course_module_ids = [
        module_id for (module_id,) in db.query(CourseModule.id).filter(
            CourseModule.course_id == course_id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).all()
    ]

    if not course_module_ids:
        return {}

    # Get progress for all these modules
    module_progress = {}
    for module_id in course_module_ids:
        mp = db.query(ModuleProgress).filter(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.module_id == module_id,
            ModuleProgress.org_id == current_user.org_id
        ).first()
        if mp:
            module_progress[str(module_id)] = mp.status
        else:
            module_progress[str(module_id)] = "not_started"

    return module_progress

@learner_router.get("/resume/{course_id}")
def resume_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get the first incomplete module for a learner in a course.
    Returns modules in sequential order (sections by sort_order, modules by sort_order within sections).
    If course is completed, returns the last module."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, course_id, current_user.org_id)

    if not cp:
        # No progress - return first module
        first_section = db.query(CourseSection).filter(
            CourseSection.course_id == course_id,
            CourseSection.org_id == current_user.org_id,
            CourseSection.deleted_at.is_(None),
        ).order_by(CourseSection.sort_order.asc()).first()

        if first_section:
            first_module = db.query(CourseModule).filter(
                CourseModule.section_id == first_section.id,
                CourseModule.org_id == current_user.org_id,
                CourseModule.deleted_at.is_(None),
            ).order_by(CourseModule.sort_order.asc()).first()
            if first_module:
                return {"status": "not_started", "last_module_id": first_module.id, "last_block_id": None}

        return {"status": "not_started"}

    # If course is submitted/completed, return last module
    if cp.status in ("completed", "submitted"):
        last_section = db.query(CourseSection).filter(
            CourseSection.course_id == course_id,
            CourseSection.org_id == current_user.org_id,
            CourseSection.deleted_at.is_(None),
        ).order_by(CourseSection.sort_order.desc()).first()

        if last_section:
            last_module = db.query(CourseModule).filter(
                CourseModule.section_id == last_section.id,
                CourseModule.org_id == current_user.org_id,
                CourseModule.deleted_at.is_(None),
            ).order_by(CourseModule.sort_order.desc()).first()
            if last_module:
                return {"status": cp.status, "last_module_id": last_module.id, "last_block_id": None}

        return {"status": cp.status}

    # Find first incomplete module sequentially
    sections = db.query(CourseSection).filter(
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).order_by(CourseSection.sort_order.asc()).all()

    for section in sections:
        # Check if section is unlocked (previous section completed)
        if section.sort_order > 0:
            previous_section = db.query(CourseSection).filter(
                CourseSection.course_id == course_id,
                CourseSection.org_id == current_user.org_id,
                CourseSection.deleted_at.is_(None),
                CourseSection.sort_order < section.sort_order,
            ).order_by(CourseSection.sort_order.desc()).first()

            if previous_section:
                prev_sp = progress_repo.get_section_progress(current_user.id, previous_section.id, current_user.org_id)
                if not prev_sp or prev_sp.status != "completed":
                    # Previous section not completed, skip this section
                    continue

        # Get modules in this section, ordered by sort_order
        modules = db.query(CourseModule).filter(
            CourseModule.section_id == section.id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).order_by(CourseModule.sort_order.asc()).all()

        for module in modules:
            mp = progress_repo.get_module_progress(current_user.id, module.id, current_user.org_id)
            if not mp or mp.status != "completed":
                # Found first incomplete module
                return {
                    "status": cp.status,
                    "last_module_id": module.id,
                    "last_block_id": mp.last_block_id if mp else None
                }

    # All modules completed but course not submitted
    return {"status": "ready_to_submit", "last_module_id": None, "last_block_id": None}

@learner_router.post("/courses/{course_id}/submit")
def submit_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Explicitly submit a course for completion.
    Validates that all modules are completed, marks course as submitted,
    and triggers certificate generation."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, course_id, current_user.org_id)
    
    if not cp:
        raise HTTPException(status_code=400, detail="No progress found for this course")
    
    # Check if certificate already exists - return it instead of error
    from app.models.certificate import Certificate
    existing_cert = db.query(Certificate).filter(
        Certificate.user_id == current_user.id,
        Certificate.course_id == course_id,
        Certificate.org_id == current_user.org_id
    ).first()
    
    if existing_cert:
        # Course already submitted and certificate exists - return the existing certificate
        return {
            "status": "success",
            "course_status": cp.status,
            "completed_at": cp.completed_at.isoformat() if cp.completed_at else None,
            "certificate": existing_cert.to_dict(),
            "already_submitted": True
        }
    
    # Verify all modules are completed
    course_module_ids = [
        module_id for (module_id,) in db.query(CourseModule.id).filter(
            CourseModule.course_id == course_id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
        ).all()
    ]
    
    completed_module_ids = {
        module_id for (module_id,) in db.query(ModuleProgress.module_id).filter(
            ModuleProgress.user_id == current_user.id,
            ModuleProgress.org_id == current_user.org_id,
            ModuleProgress.module_id.in_(course_module_ids),
            ModuleProgress.status == "completed",
        ).all()
    }
    
    if len(completed_module_ids) != len(course_module_ids):
        raise HTTPException(
            status_code=400, 
            detail=f"Complete all modules before submitting. Completed: {len(completed_module_ids)}/{len(course_module_ids)}"
        )
    
    # Mark course as submitted
    cp.status = "submitted"
    cp.completion_percentage = 100.0
    cp.completed_at = cp.completed_at or datetime.utcnow()
    
    # Emit COURSE_SUBMITTED event
    db.add(LearnerEvent(
        user_id=current_user.id,
        course_id=course_id,
        event_type="COURSE_SUBMITTED",
        schema_version="1.0",
        payload_json={
            "completed_modules": len(completed_module_ids),
            "total_modules": len(course_module_ids)
        },
        created_at=datetime.utcnow(),
        org_id=current_user.org_id
    ))
    
    progress_repo.upsert_course_progress(cp)
    PALScoreService(db).recompute_user(current_user.id, current_user.org_id)
    db.commit()
    
    # Auto-generate certificate
    cert = None
    try:
        from app.models.user import User
        from app.models.course import Course
        from app.services.certificate_service import CertificateService
        
        user = db.query(User).filter(User.id == current_user.id).first()
        course = db.query(Course).filter(Course.id == course_id, Course.org_id == current_user.org_id).first()
        
        if user and course:
            cert_service = CertificateService(db)
            cert, created = cert_service.generate_certificate(user, course, current_user.org_id)
            
            if created:
                # Emit CERTIFICATE_GENERATED event
                db.add(LearnerEvent(
                    user_id=current_user.id,
                    course_id=course_id,
                    event_type="CERTIFICATE_GENERATED",
                    schema_version="1.0",
                    payload_json={"certificate_id": cert.id},
                    created_at=datetime.utcnow(),
                    org_id=current_user.org_id
                ))
                db.commit()
    except Exception as e:
        # Log error but don't fail submission if certificate generation fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate certificate for course {course_id}: {e}")
    
    response_data = {
        "status": "success",
        "course_status": cp.status,
        "completed_at": cp.completed_at.isoformat() if cp.completed_at else None
    }
    
    if cert:
        response_data["certificate"] = cert.to_dict()
    
    return response_data

from app.models.lesson_block_progress import LessonBlockProgress

from app.services.snapshot_resolver import SnapshotResolver

def _resolve_block_for_learner(block_id: int, db: Session, user_id: str, org_id: int):
    block_with_course = db.query(LessonBlock.block_type, CourseModule.course_id).join(
        CourseModule, LessonBlock.module_id == CourseModule.id
    ).filter(LessonBlock.id == block_id, LessonBlock.org_id == org_id).first()
    if not block_with_course:
        raise HTTPException(status_code=404, detail="Block not found in database")
    _, course_id = block_with_course
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(user_id, course_id, org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")
    resolver = SnapshotResolver(db)
    try:
        return resolver.get_block(user_id, course_id, block_id, org_id), course_id
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

def _resolve_local_media_path(storage_key: str, org_id: int):
    expected_prefix = f"/uploads/media/{org_id}/"
    if not storage_key.startswith(expected_prefix):
        raise HTTPException(status_code=404, detail="Media not found")
    filename = storage_key[len(expected_prefix):]
    org_dir = (media_upload_root() / str(org_id)).resolve()
    candidate = (org_dir / filename).resolve()
    try:
        candidate.relative_to(org_dir)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Media not found") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    return candidate

def _inline_pdf_disposition(filename: str) -> str:
    fallback = "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in (filename or "document.pdf"))
    quoted = quote(filename or fallback)
    return f'inline; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'

class QuizSubmitRequest(BaseModel):
    answers: dict


@learner_router.get("/blocks/{block_id}/pdf")
def view_pdf_block(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    block, _ = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "pdf":
        raise HTTPException(status_code=400, detail="Block is not a PDF")

    settings = block.get("metadata_json") or block.get("settings") or {}
    asset_id = block.get("media_asset_id") or settings.get("asset_id")
    if not asset_id:
        raise HTTPException(status_code=404, detail="PDF asset is not configured")
    try:
        asset_id = int(asset_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="PDF asset is not configured") from exc

    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    if asset.mime_type != "application/pdf" and not asset.file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Configured asset is not a PDF")

    if asset.storage_key.startswith("/uploads/"):
        path = _resolve_local_media_path(asset.storage_key, current_user.org_id)
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=asset.file_name,
            headers={
                "Content-Disposition": _inline_pdf_disposition(asset.file_name),
                "X-Content-Type-Options": "nosniff",
            },
        )

    from app.services.r2_client import generate_presigned_download_url
    return RedirectResponse(generate_presigned_download_url(asset.storage_key), status_code=302)


def _quiz_attempt_limit(settings: dict) -> int | None:
    raw = settings.get("max_attempts", settings.get("attempt_limit", 0))
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        value = 0
    return value if value > 0 else None


def _quiz_attempt_history(db: Session, *, user_id: str, org_id: int, course_id: str, block_id: int) -> list[dict]:
    events = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == user_id,
        LearnerEvent.org_id == org_id,
        LearnerEvent.course_id == course_id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
    ).order_by(LearnerEvent.created_at.asc(), LearnerEvent.id.asc()).all()
    history = []
    for index, event in enumerate(events, start=1):
        payload = event.payload_json or {}
        score = float(payload.get("score") or 0)
        history.append({
            "attempt_id": event.id,
            "attempt_number": int(payload.get("attempt_number") or index),
            "attempt_date": event.created_at.isoformat() if event.created_at else None,
            "score": score,
            "status": "passed" if payload.get("passed") else "failed",
            "passed": bool(payload.get("passed")),
            "correct": payload.get("correct"),
            "total": payload.get("total"),
            "points_awarded": payload.get("points_awarded"),
            "points_total": payload.get("points_total"),
        })
    return history


def _quiz_stats_payload(settings: dict, history: list[dict]) -> dict:
    max_attempts = _quiz_attempt_limit(settings)
    attempts_used = len(history)
    attempts_remaining = None if max_attempts is None else max(max_attempts - attempts_used, 0)
    highest_score = max((attempt["score"] for attempt in history), default=0.0)
    latest_score = history[-1]["score"] if history else None
    best_attempt = max(history, key=lambda item: item["score"], default=None)
    average_score = sum(attempt["score"] for attempt in history) / attempts_used if attempts_used else 0.0
    completion_status = "completed" if any(attempt["passed"] for attempt in history) else "attempted" if history else "not_started"
    return {
        "maximum_attempts": max_attempts,
        "max_attempts": max_attempts,
        "attempts_used": attempts_used,
        "attempts_remaining": attempts_remaining,
        "highest_score": round(highest_score, 2),
        "latest_score": round(latest_score, 2) if latest_score is not None else None,
        "best_attempt": best_attempt,
        "average_score": round(average_score, 2),
        "completion_status": completion_status,
        "attempt_history": history,
    }


@learner_router.get("/blocks/{block_id}/quiz/stats")
async def get_quiz_stats(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    block, course_id = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") not in ("quiz", "native_quiz"):
        raise HTTPException(status_code=400, detail="Block is not a quiz")
    settings = block.get("metadata_json", {})
    history = _quiz_attempt_history(db, user_id=current_user.id, org_id=current_user.org_id, course_id=course_id, block_id=block_id)
    return _quiz_stats_payload(settings, history)


@learner_router.get("/admin/categories/{category_slug}/quiz-statistics")
def get_category_quiz_statistics(
    category_slug: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    if current_user.role == "category_admin" and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")

    learners = db.query(User).filter(
        User.role == "learner",
        User.category_scope == category_slug,
        User.org_id == current_user.org_id,
    ).order_by(User.full_name.asc()).all()
    quiz_blocks = db.query(LessonBlock, CourseModule, Course).join(
        CourseModule, LessonBlock.module_id == CourseModule.id
    ).join(
        Course, CourseModule.course_id == Course.id
    ).filter(
        LessonBlock.org_id == current_user.org_id,
        Course.org_id == current_user.org_id,
        Course.category_slug == category_slug,
        LessonBlock.block_type.in_(("quiz", "native_quiz")),
        LessonBlock.deleted_at.is_(None),
        CourseModule.deleted_at.is_(None),
    ).all()

    rows = []
    for learner in learners:
        learner_attempts = []
        for block, module, course in quiz_blocks:
            settings = block.metadata_json or {}
            history = _quiz_attempt_history(
                db,
                user_id=learner.id,
                org_id=current_user.org_id,
                course_id=course.id,
                block_id=block.id,
            )
            stats = _quiz_stats_payload(settings, history)
            learner_attempts.append({
                "course_id": course.id,
                "course_name": course.name,
                "module_id": module.id,
                "module_title": module.title,
                "block_id": block.id,
                "quiz_title": block.content or settings.get("title") or "Quiz",
                **stats,
            })
        scores = [item["highest_score"] for item in learner_attempts if item["attempts_used"] > 0]
        rows.append({
            "learner": {
                "id": learner.id,
                "full_name": learner.full_name,
                "email": learner.email,
            },
            "attempts_used": sum(item["attempts_used"] for item in learner_attempts),
            "attempts_remaining": None if any(item["attempts_remaining"] is None for item in learner_attempts) else sum(item["attempts_remaining"] for item in learner_attempts),
            "highest_score": round(max(scores), 2) if scores else 0.0,
            "latest_score": next((item["latest_score"] for item in reversed(learner_attempts) if item["latest_score"] is not None), None),
            "best_attempt": max((item["best_attempt"] for item in learner_attempts if item["best_attempt"]), key=lambda item: item["score"], default=None),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "completion_status": "completed" if any(item["completion_status"] == "completed" for item in learner_attempts) else "attempted" if scores else "not_started",
            "quizzes": learner_attempts,
        })

    return {"rows": rows}


@learner_router.post("/blocks/{block_id}/quiz/submit")
async def submit_quiz(
    block_id: int,
    request: QuizSubmitRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    block, course_id = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") not in ("quiz", "native_quiz"):
        raise HTTPException(status_code=400, detail="Block is not a quiz")
    
    settings = block.get("metadata_json", {})
    questions = settings.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Quiz has no questions")

    max_attempts = _quiz_attempt_limit(settings)
    prior_attempts = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == current_user.id,
        LearnerEvent.org_id == current_user.org_id,
        LearnerEvent.course_id == course_id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
    ).count()
    if max_attempts is not None and prior_attempts >= max_attempts:
        raise HTTPException(status_code=403, detail="You have reached the maximum number of allowed attempts.")

    correct = 0
    total = len(questions)
    total_points = 0
    awarded_points = 0
    question_results = []
    for q in questions:
        q_id = str(q.get("id"))
        correct_option_id = q.get("correct_option_id")
        if not correct_option_id:
            raise HTTPException(status_code=400, detail="Quiz question is missing a correct option")
        points = int(q.get("points") or 1)
        total_points += points
        selected_option_id = request.answers.get(q_id)
        is_correct = selected_option_id == correct_option_id
        if is_correct:
            correct += 1
            awarded_points += points
        question_results.append({
            "question_id": q_id,
            "is_correct": is_correct,
            "points": points,
            "points_awarded": points if is_correct else 0,
        })
            
    score = (awarded_points / total_points) * 100 if total_points > 0 else 0
    
    passed = score >= int(settings.get("passing_score") or 80)

    progress_repo = ProgressRepository(db)
    bp = progress_repo.get_block_progress(current_user.id, block_id, current_user.org_id)
    if not bp:
        bp = LessonBlockProgress(user_id=current_user.id, block_id=block_id, module_id=block.get("module_id"), org_id=current_user.org_id, status="completed" if passed else "in_progress", completed_at=datetime.utcnow() if passed else None)
        db.add(bp)
    else:
        if passed:
            bp.status = "completed"
            bp.completed_at = datetime.utcnow()
            
    quiz_event = LearnerEvent(
        user_id=current_user.id, course_id=course_id, module_id=block.get("module_id"), block_id=block_id,
        event_type="QUIZ_SUBMITTED", schema_version="1.0",
        payload_json={
            "score": score,
            "passed": passed,
            "correct": correct,
            "total": total,
            "points_awarded": awarded_points,
            "points_total": total_points,
            "attempt_number": prior_attempts + 1,
            "max_attempts": max_attempts,
        }, created_at=datetime.utcnow(), org_id=current_user.org_id
    )
    db.add(quiz_event)
    db.flush()

    gradebook = GradebookService(db)
    grade_item = gradebook.ensure_quiz_grade_item(
        org_id=current_user.org_id,
        course_id=course_id,
        block_id=block_id,
        title=block.get("content") or settings.get("title") or "Quiz",
        settings=settings,
        actor_user_id=current_user.id,
    )
    gradebook.upsert_current_result(
        org_id=current_user.org_id,
        course_id=course_id,
        course_version_id=gradebook.course_version_token(
            user_id=current_user.id,
            course_id=course_id,
            org_id=current_user.org_id,
        ),
        grade_item=grade_item,
        user_id=current_user.id,
        source_type="quiz_submission",
        source_id=str(quiz_event.id),
        attempt_number=prior_attempts + 1,
        points_awarded=float(awarded_points),
        points_possible=float(total_points),
        percentage=float(score),
        status="graded",
        graded_by=None,
        graded_at=quiz_event.created_at,
        feedback=None,
        metadata={
            "passed": passed,
            "correct": correct,
            "total": total,
            "attempt_number": prior_attempts + 1,
            "max_attempts": max_attempts,
            "attempt_strategy": (grade_item.grading_policy_json or {}).get("attempt_strategy", "best"),
            "question_results": question_results,
            "source_event_id": quiz_event.id,
        },
    )
    PALScoreService(db).recompute_user(current_user.id, current_user.org_id)
    db.commit()
    history = _quiz_attempt_history(db, user_id=current_user.id, org_id=current_user.org_id, course_id=course_id, block_id=block_id)
    stats = _quiz_stats_payload(settings, history)
    
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "passed": passed,
        "attempt_number": prior_attempts + 1,
        "max_attempts": max_attempts,
        "attempts_remaining": stats["attempts_remaining"],
        "attempts_used": stats["attempts_used"],
        "highest_score": stats["highest_score"],
        "latest_score": stats["latest_score"],
        "best_attempt": stats["best_attempt"],
        "attempt_history": stats["attempt_history"],
        "question_results": question_results,
    }

class PollVoteRequest(BaseModel):
    option_id: int

@learner_router.post("/blocks/{block_id}/poll/vote")
async def poll_vote(
    block_id: int,
    request: PollVoteRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    block, course_id = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "poll":
        raise HTTPException(status_code=400, detail="Block is not a poll")
    
    settings = block.get("metadata_json", block.get("settings", {}))
    options = settings.get("options", [])
    if request.option_id < 0 or request.option_id >= len(options):
        raise HTTPException(status_code=400, detail="Invalid option")
    
    # Prevent duplicate voting: check if user already voted on this poll
    existing_vote = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == current_user.id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "POLL_VOTED",
        LearnerEvent.org_id == current_user.org_id,
    ).first()
    
    allow_change = settings.get("allow_vote_change", False)
    if existing_vote and not allow_change:
        raise HTTPException(status_code=409, detail="You have already voted on this poll")
    
    if existing_vote and allow_change:
        # Update existing vote
        existing_vote.payload_json = {"option_id": request.option_id}
        existing_vote.created_at = datetime.utcnow()
    else:
        # New vote
        db.add(LearnerEvent(
            user_id=current_user.id, course_id=course_id, module_id=block.get("module_id"), block_id=block_id,
            event_type="POLL_VOTED", schema_version="1.0",
            payload_json={"option_id": request.option_id}, created_at=datetime.utcnow(), org_id=current_user.org_id
        ))
    
    progress_repo = ProgressRepository(db)
    bp = progress_repo.get_block_progress(current_user.id, str(block_id), current_user.org_id)
    if not bp:
        bp = LessonBlockProgress(user_id=current_user.id, block_id=str(block_id), module_id=block.get("module_id"), org_id=current_user.org_id, status="completed", completed_at=datetime.utcnow())
        db.add(bp)
    else:
        bp.status = "completed"
        bp.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Vote recorded", "voted": True}

@learner_router.get("/blocks/{block_id}/poll-results")
async def poll_results(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    block, course_id = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "poll":
        raise HTTPException(status_code=400, detail="Block is not a poll")
    
    settings = block.get("metadata_json", block.get("settings", {}))
    options = settings.get("options", [])
    
    # Aggregate real votes from LearnerEvent table
    vote_events = db.query(LearnerEvent).filter(
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "POLL_VOTED",
        LearnerEvent.org_id == current_user.org_id,
    ).all()
    
    vote_counts = {}
    total_votes = 0
    my_vote = []
    for evt in vote_events:
        payload = evt.payload_json or {}
        option_id = payload.get("option_id")
        if option_id is not None:
            vote_counts[option_id] = vote_counts.get(option_id, 0) + 1
            total_votes += 1
            if evt.user_id == current_user.id:
                my_vote = [option_id]
    
    results = {}
    for i, o in enumerate(options):
        opt_id = o.get("id", i)
        results[opt_id] = vote_counts.get(opt_id, vote_counts.get(i, 0))
    
    return {"results": results, "total_votes": total_votes, "my_vote": my_vote}


@learner_router.get("/blocks/{block_id}/resources/{asset_id}/download")
def download_resource(
    block_id: int,
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Return a download URL for a resource collection asset."""
    block, course_id = _resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") != "resource_collection":
        raise HTTPException(status_code=400, detail="Block is not a resource collection")
    
    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id,
        MediaAsset.deleted_at.is_(None),
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    # Generate download URL
    from app.services.r2_client import generate_presigned_download_url
    if asset.storage_key.startswith("/uploads/"):
        url = asset.storage_key
    else:
        url = generate_presigned_download_url(asset.storage_key)
    
    # Emit telemetry event
    db.add(LearnerEvent(
        user_id=current_user.id, course_id=course_id, module_id=block.get("module_id"), block_id=block_id,
        event_type="RESOURCE_DOWNLOADED", schema_version="1.0",
        payload_json={"asset_id": asset_id, "filename": asset.file_name}, created_at=datetime.utcnow(), org_id=current_user.org_id
    ))
    db.commit()
    
    return {"url": url, "filename": asset.file_name}

