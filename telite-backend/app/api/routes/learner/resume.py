"""Learner resume and submit course endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.pal_score_service import PALScoreService
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.module_progress import ModuleProgress
from app.models.certificate import Certificate
from app.models.user import User
from app.models.course import Course
from app.models.learner_event import LearnerEvent
from app.services.certificate_service import CertificateService

logger = logging.getLogger(__name__)

learner_resume_router = APIRouter(tags=["Learner Resume APIs"])


@learner_resume_router.get("/resume/{course_id}")
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
                # Check if previous section is completed (both modules and time requirement)
                if not prev_sp or prev_sp.status != "completed":
                    # Previous section not completed, skip this section
                    continue
                
                # Additionally check if minimum time requirement is met (same logic as MinimumSectionTimeEvaluator)
                if previous_section.minimum_time_seconds and previous_section.minimum_time_seconds > 0:
                    time_spent = (prev_sp.time_spent_seconds if prev_sp else 0) or 0
                    if time_spent < previous_section.minimum_time_seconds:
                        # Time requirement not met, skip this section
                        logger.info(
                            f"Resume: Previous section {previous_section.id} time requirement not met "
                            f"(spent {time_spent}s, required {previous_section.minimum_time_seconds}s)"
                        )
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


@learner_resume_router.post("/courses/{course_id}/submit")
def submit_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Explicitly submit a course for completion.
    Validates that all modules are completed, marks course as submitted,
    and triggers certificate generation."""
    from app.models.course_progress import CourseProgress
    from app.models.learning_path import LearningPathCourse
    from app.services.learning_path_unlock_service import LearningPathUnlockService
    
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, course_id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    progress_repo = ProgressRepository(db)
    cp = progress_repo.get_course_progress(current_user.id, course_id, current_user.org_id)
    
    if not cp:
        raise HTTPException(status_code=400, detail="No progress found for this course")
    
    # Check if certificate already exists - return it instead of error
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
    
    # Auto-generate certificate (separate transaction to not fail submission on error)
    cert = None
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        course = db.query(Course).filter(Course.id == course_id, Course.org_id == current_user.org_id).first()
        
        logger.info(f"Attempting to generate certificate for user {current_user.id}, course {course_id}")
        logger.info(f"User found: {user is not None}, Course found: {course is not None}")
        
        if user and course:
            cert_service = CertificateService(db)
            cert, created = cert_service.generate_certificate(user, course, current_user.org_id, commit=True)
            
            logger.info(f"Certificate generation result: created={created}, cert={cert is not None}")
            if cert:
                logger.info(f"Certificate ID: {cert.id}, Token: {cert.verification_token}")
            
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
        logger.error(f"Failed to generate certificate for course {course_id}: {e}", exc_info=True)
    
    response_data = {
        "status": "success",
        "course_status": cp.status,
        "completed_at": cp.completed_at.isoformat() if cp.completed_at else None
    }
    
    if cert:
        response_data["certificate"] = cert.to_dict()
    
    return response_data
