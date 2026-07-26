"""Learner course-related endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.repositories.learner_repo import LearnerRepository
from app.repositories.enrollment_repo import EnrollmentRepository
from app.api.routes.learner.schemas import CourseListResponse
from app.api.routes.learner.utils import sanitize_block_for_learner

logger = logging.getLogger(__name__)

learner_courses_router = APIRouter(tags=["Learner Course APIs"])


@learner_courses_router.get("/courses", response_model=List[CourseListResponse])
def get_learner_courses(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve courses available/enrolled for the learner."""
    learner_repo = LearnerRepository(db)
    courses = learner_repo.get_enrolled_courses(current_user.id, current_user.org_id)
    return [
        CourseListResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            slug=c.slug,
            status=c.status,
            enrolled_count=c.enrolled_count,
            completion_rate=c.completion_rate,
            modules_count=c.module_count,
            tier=c.tier,
            cover_image_url=c.cover_image_url,
            category_slug=c.category_slug
        ) for c in courses
    ]


@learner_courses_router.get("/paths")
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


@learner_courses_router.get("/paths/{id}")
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


@learner_courses_router.get("/courses/{id}")
def get_learner_course(
    id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve details for a specific course, gated by enrollment access.
    Serves snapshot-frozen content when learner has an enrolled_version.
    Returns sections ordered by sort_order ASC, modules ordered by sort_order ASC within sections."""
    from app.models.course_version import CourseVersion
    from app.models.course_section import CourseSection
    from app.models.course_module import CourseModule
    from app.models.lesson_block import LessonBlock
    from app.repositories.progress_repo import ProgressRepository
    from app.models.course_progress import CourseProgress
    
    enrollment_repo = EnrollmentRepository(db)
    if not enrollment_repo.has_access(current_user.id, id, current_user.org_id):
        raise HTTPException(status_code=403, detail="Not enrolled or access denied")

    learner_repo = LearnerRepository(db)
    course = learner_repo.get_course(id, current_user.id, current_user.org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check if learner is pinned to a specific version
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
                        blocks[idx] = sanitize_block_for_learner(b)
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
            block_dict = sanitize_block_for_learner(block_dict)
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


@learner_courses_router.get("/modules/{id}")
def get_learner_module(
    id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Retrieve module data. Assuming module ID maps to course access."""
    from app.models.course_module import CourseModule
    from app.services.progression_rule_engine import ProgressionRuleEngine
    
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
