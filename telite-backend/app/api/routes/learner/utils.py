"""Learner API utility functions."""

import copy
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.storage_paths import media_upload_root
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.lesson_block_progress import LessonBlockProgress
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.snapshot_resolver import SnapshotResolver

logger = logging.getLogger(__name__)


def sanitize_quiz_settings(settings: dict | None) -> dict:
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


def sanitize_block_for_learner(block: dict) -> dict:
    """Sanitize block content for learner consumption."""
    safe_block = copy.deepcopy(block)
    block_type = safe_block.get("block_type")
    settings = safe_block.get("metadata_json") or safe_block.get("settings") or {}
    if block_type in ("quiz", "native_quiz"):
        settings = sanitize_quiz_settings(settings)
    safe_block["settings"] = settings
    safe_block["metadata_json"] = settings
    return safe_block


def module_section_id(db: Session, module_id: int | None, org_id: int) -> int | None:
    """Get the section ID for a given module."""
    if not module_id:
        return None
    module = db.query(CourseModule).filter(
        CourseModule.id == module_id,
        CourseModule.org_id == org_id
    ).first()
    return module.section_id if module else None


def resolve_block_for_learner(block_id: int, db: Session, user_id: str, org_id: int):
    """Resolve a block for a learner, checking enrollment access."""
    block_with_course = db.query(LessonBlock.block_type, CourseModule.course_id).join(
        CourseModule, LessonBlock.module_id == CourseModule.id
    ).filter(
        LessonBlock.id == block_id,
        LessonBlock.org_id == org_id
    ).first()
    
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


def resolve_local_media_path(storage_key: str, org_id: int):
    """Resolve local media storage path with security checks."""
    if storage_key.startswith("org_"):
        expected_prefix = f"org_{org_id}/"
        if not storage_key.startswith(expected_prefix):
            raise HTTPException(status_code=404, detail="Media not found")
        filename = storage_key[len(expected_prefix):]
        org_dir = (media_upload_root() / f"org_{org_id}").resolve()
    else:
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


def inline_pdf_disposition(filename: str) -> str:
    """Generate Content-Disposition header for inline PDF viewing."""
    fallback = "".join(
        ch if ch.isalnum() or ch in ".-_" else "_"
        for ch in (filename or "document.pdf")
    )
    quoted = quote(filename or fallback)
    return f'inline; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'


def apply_active_seconds(
    db: Session,
    *,
    current_user,
    course_id: str,
    module_id: int | None,
    block_id: int | None,
    active_seconds: int,
) -> None:
    """Apply active seconds to course, module, and block progress."""
    from app.api.auth import TokenData
    from app.models.course_progress import CourseProgress
    from app.models.module_progress import ModuleProgress
    
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
        from app.models.learner_event import LearnerEvent
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
            mp = ModuleProgress(
                user_id=current_user.id,
                module_id=module_id,
                org_id=current_user.org_id,
                status="in_progress",
                started_at=now
            )
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
            bp = LessonBlockProgress(
                user_id=current_user.id,
                module_id=module_id,
                block_id=block_id,
                org_id=current_user.org_id,
                status="not_started"
            )
        bp.time_spent_seconds = (bp.time_spent_seconds or 0) + seconds
        bp.last_viewed_at = now
        progress_repo.upsert_block_progress(bp)

    # Track section-level time
    section_id = module_section_id(db, module_id, current_user.org_id)
    if section_id:
        from app.models.section_progress import SectionProgress
        sp = progress_repo.get_section_progress(current_user.id, section_id, current_user.org_id)
        if not sp:
            sp = SectionProgress(
                user_id=current_user.id,
                section_id=section_id,
                org_id=current_user.org_id,
                status="in_progress",
                completion_percentage=0.0,
                time_spent_seconds=0,
                started_at=now,
                last_entered_at=now,
            )
        else:
            sp.time_spent_seconds = (sp.time_spent_seconds or 0) + seconds
            sp.last_entered_at = sp.last_entered_at or now
            sp.last_left_at = now
        
        # Check if section should be marked as completed based on time requirement
        section = db.query(CourseSection).filter(
            CourseSection.id == section_id,
            CourseSection.org_id == current_user.org_id
        ).first()
        
        if section and sp.status != "completed":
            # Count completed modules in this section
            section_modules = db.query(CourseModule).filter(
                CourseModule.section_id == section_id,
                CourseModule.org_id == current_user.org_id,
                CourseModule.deleted_at.is_(None)
            ).all()
            
            completed_in_section = 0
            for mod in section_modules:
                mp = db.query(ModuleProgress).filter(
                    ModuleProgress.user_id == current_user.id,
                    ModuleProgress.module_id == mod.id,
                    ModuleProgress.org_id == current_user.org_id
                ).first()
                if mp and mp.status == "completed":
                    completed_in_section += 1
            
            # Check if minimum time requirement is met
            time_requirement_met = True
            if section.minimum_time_seconds and section.minimum_time_seconds > 0:
                time_requirement_met = (sp.time_spent_seconds or 0) >= section.minimum_time_seconds
            
            # Auto-complete section if all modules completed AND time requirement is met
            if completed_in_section == len(section_modules) and time_requirement_met:
                sp.status = "completed"
                sp.completed_at = now
                logger.info(f"Section {section_id} marked as completed via heartbeat (time requirement met)")
            elif len(section_modules) == 0:
                sp.status = "completed"
                sp.completed_at = now
                logger.info(f"Section {section_id} has no modules, marked as completed")
        
        progress_repo.upsert_section_progress(sp)

    from app.models.learner_event import LearnerEvent
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
