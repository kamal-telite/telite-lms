"""Learner API Endpoints."""

import copy
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
from app.services.completion_policy_service import CompletionPolicyService
from app.services.gradebook_service import GradebookService
from app.services.learning_path_unlock_service import LearningPathUnlockService
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset

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
    Serves snapshot-frozen content when learner has an enrolled_version."""
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
            snapshot_modules = []
            for section in snapshot.get("sections", []):
                for mod in section.get("modules", []):
                    blocks = mod.get("blocks", [])
                    for idx, b in enumerate(blocks):
                        blocks[idx] = _sanitize_block_for_learner(b)
                    snapshot_modules.append({
                        "id": mod["id"],
                        "title": mod.get("title", ""),
                        "module_type": mod.get("module_type", "page"),
                        "sort_order": mod.get("sort_order", 0),
                        "section_id": mod.get("section_id"),
                        "status": mod.get("status", "published"),
                        "content_url": mod.get("content_url"),
                        "content": blocks,
                    })
            return {
                "id": course.id,
                "name": snapshot.get("course", {}).get("name", course.name),
                "description": course.description,
                "modules_json": snapshot_modules,
                "version": enrolled_version,
            }

    # Fallback: serve live draft content
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
            block_dict = _sanitize_block_for_learner(block_dict)
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

    if not total_modules or completed_count != total_modules:
        course_progress.status = "in_progress"
        course_progress.completed_at = None

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
        return resolver.get_block(user_id, course_id, block_id), course_id
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

class QuizSubmitRequest(BaseModel):
    answers: dict

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

    max_attempts = int(settings.get("max_attempts") or 0)
    prior_attempts = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == current_user.id,
        LearnerEvent.org_id == current_user.org_id,
        LearnerEvent.course_id == course_id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
    ).count()
    if max_attempts > 0 and prior_attempts >= max_attempts:
        raise HTTPException(status_code=403, detail="Maximum quiz attempts reached")

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
    db.commit()
    
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "passed": passed,
        "attempt_number": prior_attempts + 1,
        "max_attempts": max_attempts,
        "attempts_remaining": max(max_attempts - prior_attempts - 1, 0) if max_attempts > 0 else None,
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

