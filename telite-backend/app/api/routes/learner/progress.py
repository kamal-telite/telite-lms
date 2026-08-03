"""Learner progress-related endpoints."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.completion_policy_service import CompletionPolicyService
from app.services.pal_score_service import PALScoreService
from app.services.learning_path_unlock_service import LearningPathUnlockService
from app.models.learner_event import LearnerEvent
from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.section_progress import SectionProgress
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.api.routes.learner.schemas import (
    ProgressMutationRequest,
    HeartbeatRequest,
    LearningSessionStartRequest,
    LearningSessionHeartbeatRequest,
    LearningSessionEndRequest,
)

logger = logging.getLogger(__name__)

learner_progress_router = APIRouter(tags=["Learner Progress APIs"])


@learner_progress_router.post("/progress")
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
            user_id=current_user.id,
            course_id=req.course_id,
            org_id=current_user.org_id,
            status="in_progress",
            completion_percentage=0.0,
            started_at=datetime.utcnow()
        )
    
    for mod_upd in req.module_updates:
        mp = progress_repo.get_module_progress(current_user.id, mod_upd.module_id, current_user.org_id)
        if not mp:
            mp = ModuleProgress(
                user_id=current_user.id,
                module_id=mod_upd.module_id,
                org_id=current_user.org_id,
                status=mod_upd.status,
                started_at=datetime.utcnow()
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
        
        logger.info(
            f"Processing section {section.id} ('{section.title}') during progress update: "
            f"has {len(section_modules)} modules, "
            f"minimum_time_seconds={section.minimum_time_seconds} (type: {type(section.minimum_time_seconds)}), "
            f"section_id={section.id}, section_id_type={type(section.id)}"
        )
        
        if not section_modules:
            # Section has no modules - mark as completed immediately
            sp = progress_repo.get_section_progress(current_user.id, section.id, current_user.org_id)
            if not sp:
                sp = SectionProgress(
                    user_id=current_user.id,
                    section_id=section.id,
                    org_id=current_user.org_id,
                    status="completed",
                    completion_percentage=100.0,
                    time_spent_seconds=0,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
            elif sp.status != "completed":
                sp.status = "completed"
                sp.completion_percentage = 100.0
                sp.completed_at = datetime.utcnow()
            progress_repo.upsert_section_progress(sp)
            logger.info(f"Section {section.id} has no modules, marked as completed")
            continue
        
        # Count completed modules in this section
        completed_in_section = 0
        for module in section_modules:
            mp = progress_repo.get_module_progress(current_user.id, module.id, current_user.org_id)
            if mp and mp.status == "completed":
                completed_in_section += 1
            logger.info(f"Module {module.id} in section {section.id}: status={mp.status if mp else 'no progress'}")
        
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
        
        # A section is complete only when all of its modules are complete and
        # its configured minimum time has been satisfied.
        time_requirement_met = True
        if section.minimum_time_seconds and section.minimum_time_seconds > 0:
            time_requirement_met = (sp.time_spent_seconds or 0) >= section.minimum_time_seconds
            logger.info(
                f"Time requirement check: Section '{section.title}' requires {section.minimum_time_seconds}s, "
                f"spent {sp.time_spent_seconds}s, met: {time_requirement_met}"
            )
        
        logger.info(
            f"Section completion check during progress update - Section ID: {section.id}, "
            f"Section title: {section.title}, "
            f"User: {current_user.id}, "
            f"Modules completed: {completed_in_section}/{len(section_modules)}, "
            f"Time spent: {sp.time_spent_seconds}s, "
            f"Minimum required: {section.minimum_time_seconds}s, "
            f"Time requirement met: {time_requirement_met}, "
            f"Current status: {sp.status}"
        )
        
        should_complete = completed_in_section == len(section_modules) and time_requirement_met
        
        if should_complete and sp.status != "completed":
            sp.status = "completed"
            sp.completed_at = datetime.utcnow()
            logger.info(f"Section {section.id} marked as completed during progress update (time met: {time_requirement_met}, modules complete: {completed_in_section == len(section_modules)})")
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

    if course_progress.status != "submitted":
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
        db.add(LearnerEvent(
            user_id=current_user.id,
            course_id=req.course_id,
            event_type="COURSE_COMPLETED",
            schema_version="1.0",
            payload_json=evaluation.to_event_payload(),
            created_at=datetime.utcnow(),
            org_id=current_user.org_id
        ))
        
        # Automatically generate certificate if eligible
        eligibility = CompletionPolicyService(db).is_certificate_eligible(
            user_id=current_user.id,
            course_id=req.course_id,
            org_id=current_user.org_id,
        )
        if eligibility.eligible:
            from app.services.certificate_service import CertificateService
            from app.models.notification import NotificationType
            from app.repositories.notification_repo import NotificationRepository
            from app.core.notification_payloads import (
                certificate_awarded_idempotency_key,
                certificate_awarded_metadata,
            )
            from app.models.user import User
            from app.models.course import Course
            try:
                user = db.query(User).filter(User.id == current_user.id).first()
                course = db.query(Course).filter(Course.id == req.course_id).first()
                
                if user and course:
                    cert_service = CertificateService(db)
                    cert, created = cert_service.generate_certificate(user, course, current_user.org_id, commit=False)
                    if created:
                        metadata = certificate_awarded_metadata(
                            course_id=cert.course_id,
                            certificate_id=cert.id,
                            verification_token=cert.verification_token,
                        )
                        NotificationRepository(db).create_once(
                            user_id=cert.user_id,
                            org_id=cert.org_id,
                            title="Certificate Awarded",
                            body=f"Your certificate for {course.name} is ready.",
                            notif_type=NotificationType.CERTIFICATE_AWARDED,
                            source_type="certificate",
                            source_id=cert.id,
                            metadata=metadata,
                            idempotency_key=certificate_awarded_idempotency_key(
                                user_id=cert.user_id,
                                certificate_id=cert.id,
                            ),
                        )
            except Exception as e:
                logger.exception("Failed to auto-generate certificate during progress update")

    progress_repo.upsert_course_progress(course_progress)
    PALScoreService(db).recompute_user(current_user.id, current_user.org_id)

    if evaluation.completed_now:
        from app.models.learning_path import LearningPathCourse
        unlock_svc = LearningPathUnlockService(db)
        
        path_courses = db.query(LearningPathCourse).filter_by(course_id=req.course_id).all()
        for pc in path_courses:
            unlock_svc.evaluate_unlocks(current_user.id, pc.path_id, current_user.org_id)

    # Single atomic commit for all progress updates
    db.commit()

    return {"status": "success", "course_status": course_progress.status}


@learner_progress_router.post("/heartbeat")
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

        section = db.query(CourseSection).join(
            CourseModule,
            CourseModule.section_id == CourseSection.id,
        ).filter(
            CourseModule.id == req.module_id,
            CourseModule.org_id == current_user.org_id,
            CourseModule.deleted_at.is_(None),
            CourseSection.org_id == current_user.org_id,
            CourseSection.deleted_at.is_(None),
        ).first()
        if section:
            sp = progress_repo.get_section_progress(current_user.id, section.id, current_user.org_id)
            if not sp:
                sp = SectionProgress(
                    user_id=current_user.id,
                    section_id=section.id,
                    org_id=current_user.org_id,
                    status="in_progress",
                    completion_percentage=0.0,
                    time_spent_seconds=0,
                    started_at=now,
                    last_entered_at=now,
                )
            elif sp.status == "not_started":
                sp.status = "in_progress"
                sp.started_at = sp.started_at or now

            sp.time_spent_seconds = (sp.time_spent_seconds or 0) + req.time_spent_seconds
            sp.last_entered_at = sp.last_entered_at or now
            sp.last_left_at = now
            progress_repo.upsert_section_progress(sp)

    # Single atomic commit for all heartbeat updates
    db.commit()
    return {"status": "success"}


@learner_progress_router.post("/learning-sessions/start")
def start_learning_session(
    req: LearningSessionStartRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    from app.models.learning_session import LearningSession
    from app.api.routes.learner.utils import module_section_id
    
    if not EnrollmentRepository(db).has_access(current_user.id, req.course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")
    now = datetime.now(timezone.utc)
    session = LearningSession(
        user_id=current_user.id,
        course_id=req.course_id,
        module_id=req.module_id,
        section_id=module_section_id(db, req.module_id, current_user.org_id),
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


@learner_progress_router.post("/learning-sessions/heartbeat")
def heartbeat_learning_session(
    req: LearningSessionHeartbeatRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    from app.models.learning_session import LearningSession
    from app.api.routes.learner.utils import module_section_id, apply_active_seconds
    
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
    session.section_id = module_section_id(db, req.module_id, current_user.org_id)
    session.block_id = req.block_id
    session.active_seconds = (session.active_seconds or 0) + seconds
    session.last_heartbeat_at = datetime.now(timezone.utc)
    apply_active_seconds(
        db,
        current_user=current_user,
        course_id=req.course_id,
        module_id=req.module_id,
        block_id=req.block_id,
        active_seconds=seconds,
    )
    db.commit()
    return {"session": session.to_dict()}


@learner_progress_router.post("/learning-sessions/end")
def end_learning_session(
    req: LearningSessionEndRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user),
):
    from app.models.learning_session import LearningSession
    
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
