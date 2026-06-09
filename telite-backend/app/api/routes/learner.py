"""Learner API Endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.repositories.learner_repo import LearnerRepository
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.learning_path_unlock_service import LearningPathUnlockService
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock

learner_router = APIRouter(prefix="/learner", tags=["Learner APIs"])

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
    """Retrieve details for a specific course, gated by enrollment access."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    learner_repo = LearnerRepository(db)
    course = learner_repo.get_course(id, current_user.id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    modules = db.query(CourseModule).filter(
        CourseModule.course_id == course.id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).order_by(CourseModule.sort_order).all()

    blocks_by_module = {}
    if modules:
        module_ids = [module.id for module in modules]
        blocks = db.query(LessonBlock).filter(
            LessonBlock.module_id.in_(module_ids),
            LessonBlock.org_id == current_user.org_id,
            LessonBlock.deleted_at.is_(None),
        ).order_by(LessonBlock.sort_order).all()
        for block in blocks:
            block_dict = block.to_dict()
            block_dict["settings"] = block_dict.pop("metadata_json", {})
            blocks_by_module.setdefault(block.module_id, []).append(block_dict)

    native_modules = []
    for module in modules:
        module_dict = module.to_dict()
        module_dict["content"] = blocks_by_module.get(module.id, [])
        native_modules.append(module_dict)
        
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "modules_json": native_modules or course.modules_json,
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
    """Update learner progress for course and modules."""
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

    if total_modules and completed_count == total_modules:
        if course_progress.status != "completed":
            course_progress.status = "completed"
            if not course_progress.completed_at:
                course_progress.completed_at = datetime.utcnow()
            course_progress.completion_percentage = 100.0
            
            # Emit COURSE_COMPLETED event
            db.add(LearnerEvent(
                user_id=current_user.id,
                course_id=req.course_id,
                event_type="COURSE_COMPLETED",
                schema_version="1.0",
                payload_json={},
                created_at=datetime.utcnow(),
                org_id=current_user.org_id
            ))
    else:
        course_progress.status = "in_progress"
        course_progress.completed_at = None

    progress_repo.upsert_course_progress(course_progress)
    db.commit()

    if course_progress.status == "completed":
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

@learner_router.get("/resume/{course_id}")
def resume_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get the last known position for a learner in a course."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, course_id, current_user.org_id)
    
    if not cp:
        return {"status": "not_started"}
        
    # In a full impl, we'd query module_progress ordering by last_viewed_at DESC
    from sqlalchemy import desc
    stmt = db.query(ModuleProgress).join(CourseModule, ModuleProgress.module_id == CourseModule.id)\
        .filter(ModuleProgress.user_id == current_user.id, CourseModule.course_id == course_id)\
        .order_by(desc(ModuleProgress.last_viewed_at)).first()
        
    if stmt:
        return {
            "status": cp.status,
            "last_module_id": stmt.module_id,
            "last_block_id": stmt.last_block_id
        }
        
    return {"status": cp.status}
