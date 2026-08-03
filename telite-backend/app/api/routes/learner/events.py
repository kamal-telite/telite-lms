"""Learner event and access validation endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.progression_rule_engine import ProgressionRuleEngine
from app.models.learner_event import LearnerEvent
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.module_progress import ModuleProgress
from app.models.section_progress import SectionProgress
from app.api.routes.learner.schemas import (
    LearnerEventsBatchRequest,
    AccessValidationRequest,
)

logger = logging.getLogger(__name__)

learner_events_router = APIRouter(tags=["Learner Event APIs"])


@learner_events_router.post("/events")
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


@learner_events_router.post("/validate-access")
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


@learner_events_router.get("/courses/{course_id}/module-progress")
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


@learner_events_router.get("/courses/{course_id}/section-progress")
def get_section_progress(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get all section progress for a course.
    Returns a mapping of section_id -> {time_spent_seconds, status} for all sections in the course."""
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    # Get all sections for this course
    course_sections = db.query(CourseSection).filter(
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).all()

    if not course_sections:
        return {}

    # Get progress for all these sections
    section_progress = {}
    for section in course_sections:
        sp = db.query(SectionProgress).filter(
            SectionProgress.user_id == current_user.id,
            SectionProgress.section_id == section.id,
            SectionProgress.org_id == current_user.org_id
        ).first()
        if sp:
            section_progress[str(section.id)] = {
                "time_spent_seconds": sp.time_spent_seconds or 0,
                "status": sp.status or "not_started",
                "minimum_time_seconds": section.minimum_time_seconds or 0
            }
        else:
            section_progress[str(section.id)] = {
                "time_spent_seconds": 0,
                "status": "not_started",
                "minimum_time_seconds": section.minimum_time_seconds or 0
            }
        
        # Debug logging
        logger.info(
            f"Section progress for section {section.id}: "
            f"status={section_progress[str(section.id)]['status']}, "
            f"time_spent={section_progress[str(section.id)]['time_spent_seconds']}s, "
            f"minimum_time={section.minimum_time_seconds}s"
        )

    return section_progress
