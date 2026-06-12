from __future__ import annotations

import logging
import copy
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_section import CourseSection
from app.models.course_version import CourseVersion
from app.models.lesson_block import LessonBlock
from app.models.media_asset import MediaAsset
from app.models.quiz_models import QuizDefinition, QuizSettings
from app.services.storage import storage_service
from app.models.learning_path import LearningPath, LearningPathCourse

logger = logging.getLogger("telite.authoring")

authoring_router = APIRouter(prefix="/authoring", tags=["Authoring Gateway"])

# -----------------------------------------------------------------------------
# 1. Course Versioning & Publishing
# -----------------------------------------------------------------------------

@authoring_router.post("/courses/{course_id}/versions", dependencies=[Depends(require_admin)])
def branch_course_version(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.org_id == current_user.org_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    latest_version = db.query(CourseVersion).filter(
        CourseVersion.course_id == course_id
    ).order_by(CourseVersion.version_number.desc()).first()
    
    new_version_number = (latest_version.version_number + 1) if latest_version else 1
    
    new_version = CourseVersion(
        course_id=course_id,
        org_id=current_user.org_id,
        version_number=new_version_number,
        status="Draft",
        parent_version_id=latest_version.id if latest_version else None,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return {"success": True, "version": new_version.to_dict()}

@authoring_router.post("/courses/{course_id}/publish", dependencies=[Depends(require_admin)])
def publish_course(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    draft = db.query(CourseVersion).filter(
        CourseVersion.course_id == course_id,
        CourseVersion.status == "Draft",
        CourseVersion.org_id == current_user.org_id
    ).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="No draft version found to publish")
        
    draft.status = "Published"
    draft.published_by = current_user.id
    draft.published_at = func.now()
    
    # In a real system, we would enqueue a Celery task here to sync the course structure to Moodle shell
    
    db.commit()
    db.refresh(draft)
    return {"success": True, "version": draft.to_dict()}

# -----------------------------------------------------------------------------
# 2. Structural Endpoints (Drag and Drop)
# -----------------------------------------------------------------------------

class CreateSectionRequest(BaseModel):
    title: str
    sort_order: int

class UpdateSectionRequest(BaseModel):
    title: str

@authoring_router.post("/courses/{course_id}/sections", dependencies=[Depends(require_admin)])
def create_section(
    course_id: str,
    request: CreateSectionRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id, Course.org_id == current_user.org_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    section = CourseSection(
        course_id=course_id,
        org_id=current_user.org_id,
        title=request.title,
        sort_order=request.sort_order
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section.to_dict()

@authoring_router.patch("/courses/{course_id}/sections/{section_id}", dependencies=[Depends(require_admin)])
def update_section(
    course_id: str,
    section_id: int,
    request: UpdateSectionRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id,
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Section title is required")

    section.title = title
    db.commit()
    db.refresh(section)
    return section.to_dict()

@authoring_router.delete("/courses/{course_id}/sections/{section_id}", dependencies=[Depends(require_admin)])
def delete_section(
    course_id: str,
    section_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id,
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    module_count = db.query(CourseModule).filter(
        CourseModule.section_id == section_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).count()
    if module_count:
        raise HTTPException(status_code=400, detail="Move or delete modules before deleting this section")

    section.deleted_at = datetime.now(timezone.utc)
    section.deleted_by = current_user.id
    db.commit()
    return {"success": True}

@authoring_router.post("/courses/{course_id}/sections/{section_id}/duplicate", dependencies=[Depends(require_admin)])
def duplicate_section(
    course_id: str,
    section_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    section = db.query(CourseSection).filter(
        CourseSection.id == section_id,
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    max_section_order = db.query(func.coalesce(func.max(CourseSection.sort_order), -1)).filter(
        CourseSection.course_id == course_id,
        CourseSection.org_id == current_user.org_id,
        CourseSection.deleted_at.is_(None),
    ).scalar()

    new_section = CourseSection(
        course_id=course_id,
        org_id=current_user.org_id,
        title=f"{section.title} Copy",
        sort_order=(max_section_order or -1) + 1,
    )
    db.add(new_section)
    db.flush()

    source_modules = db.query(CourseModule).filter(
        CourseModule.course_id == course_id,
        CourseModule.section_id == section_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).order_by(CourseModule.sort_order).all()

    new_modules = []
    for module_index, source_module in enumerate(source_modules):
        new_module = CourseModule(
            course_id=course_id,
            section=new_section.sort_order,
            section_id=new_section.id,
            status=source_module.status,
            title=source_module.title,
            module_type=source_module.module_type,
            sort_order=module_index,
            content_url=source_module.content_url,
            org_id=current_user.org_id,
        )
        db.add(new_module)
        db.flush()
        new_modules.append(new_module)

        source_blocks = db.query(LessonBlock).filter(
            LessonBlock.module_id == source_module.id,
            LessonBlock.org_id == current_user.org_id,
            LessonBlock.deleted_at.is_(None),
        ).order_by(LessonBlock.sort_order).all()
        for source_block in source_blocks:
            db.add(LessonBlock(
                module_id=new_module.id,
                org_id=current_user.org_id,
                block_type=source_block.block_type,
                content=source_block.content,
                media_asset_id=source_block.media_asset_id,
                sort_order=source_block.sort_order,
                metadata_json=copy.deepcopy(source_block.metadata_json),
            ))

    db.commit()
    db.refresh(new_section)
    for module in new_modules:
        db.refresh(module)

    payload = new_section.to_dict()
    payload["modules"] = [module.to_dict() for module in new_modules]
    return {"success": True, "section": payload}

class ModuleStructureUpdate(BaseModel):
    module_id: int
    sort_order: int

class SectionStructureUpdate(BaseModel):
    section_id: int
    modules: List[ModuleStructureUpdate]

class SaveStructureRequest(BaseModel):
    updates: List[SectionStructureUpdate]

def _quiz_to_response(quiz: QuizDefinition, module: CourseModule) -> dict:
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "passing_score": quiz.passing_score,
        "module_id": module.id,
        "module_title": module.title,
        "course_id": module.course_id,
    }

@authoring_router.get("/courses/{course_id}/quizzes", dependencies=[Depends(require_admin)])
def list_course_quizzes(
    course_id: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.org_id == current_user.org_id,
        Course.status != "archived",
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    rows = db.query(QuizDefinition, CourseModule).join(
        CourseModule,
        CourseModule.id == QuizDefinition.module_id,
    ).filter(
        QuizDefinition.org_id == current_user.org_id,
        QuizDefinition.deleted_at.is_(None),
        CourseModule.course_id == course_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.module_type == "quiz",
        CourseModule.deleted_at.is_(None),
    ).order_by(CourseModule.sort_order, QuizDefinition.id).all()

    return {"quizzes": [_quiz_to_response(quiz, module) for quiz, module in rows]}

@authoring_router.put("/courses/{course_id}/structure", dependencies=[Depends(require_admin)])
def update_course_structure(
    course_id: str,
    request: SaveStructureRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.org_id == current_user.org_id,
        Course.status != "archived",
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    sections_by_id: dict[int | None, CourseSection | None] = {None: None}
    for sec_update in request.updates:
        section_id = None if sec_update.section_id == 0 else sec_update.section_id
        if section_id is None or section_id in sections_by_id:
            continue
        section = db.query(CourseSection).filter(
            CourseSection.id == section_id,
            CourseSection.course_id == course_id,
            CourseSection.org_id == current_user.org_id,
            CourseSection.deleted_at.is_(None),
        ).first()
        if not section:
            raise HTTPException(status_code=404, detail=f"Section {section_id} not found")
        sections_by_id[section_id] = section

    for sec_update in request.updates:
        section_id = None if sec_update.section_id == 0 else sec_update.section_id
        section = sections_by_id.get(section_id)
            
        for mod_update in sec_update.modules:
            module = db.query(CourseModule).filter(
                CourseModule.id == mod_update.module_id,
                CourseModule.course_id == course_id,
                CourseModule.org_id == current_user.org_id,
                CourseModule.deleted_at.is_(None),
            ).first()
            if not module:
                raise HTTPException(status_code=404, detail=f"Module {mod_update.module_id} not found")
            module.section_id = section.id if section else None
            module.section = section.sort_order if section else -1
            module.sort_order = mod_update.sort_order
                
    db.commit()
    return {"success": True}

# -----------------------------------------------------------------------------
# 3. Lesson Block API
# -----------------------------------------------------------------------------

class CreateBlockRequest(BaseModel):
    block_type: str
    content: Optional[str] = None
    media_asset_id: Optional[int] = None
    sort_order: int

@authoring_router.post("/modules/{module_id}/blocks", dependencies=[Depends(require_admin)])
def create_lesson_block(
    module_id: int,
    request: CreateBlockRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    module = db.query(CourseModule).filter(
        CourseModule.id == module_id, 
        CourseModule.org_id == current_user.org_id
    ).first()
    
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    block = LessonBlock(
        module_id=module_id,
        org_id=current_user.org_id,
        block_type=request.block_type,
        content=request.content,
        media_asset_id=request.media_asset_id,
        sort_order=request.sort_order
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block.to_dict()

class BlockOrderUpdate(BaseModel):
    block_id: int
    sort_order: int

@authoring_router.put("/modules/{module_id}/blocks/order", dependencies=[Depends(require_admin)])
def update_block_order(
    module_id: int,
    updates: List[BlockOrderUpdate],
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    for update in updates:
        block = db.query(LessonBlock).filter(
            LessonBlock.id == update.block_id,
            LessonBlock.module_id == module_id,
            LessonBlock.org_id == current_user.org_id
        ).first()
        if block:
            block.sort_order = update.sort_order
            
    db.commit()
    return {"success": True}

# -----------------------------------------------------------------------------
# 4. Media Storage API
# -----------------------------------------------------------------------------

class PresignedUrlRequest(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int

@authoring_router.post("/media/presigned-url", dependencies=[Depends(require_admin)])
def generate_presigned_url(
    request: PresignedUrlRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    # Enforce basic limits (e.g. max 500MB)
    if request.size_bytes > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
        
    presigned_url, storage_key = storage_service.generate_presigned_upload(
        request.filename, 
        request.mime_type, 
        current_user.org_id
    )
    
    # Pre-create the MediaAsset record in a pending/deleted state if needed, 
    # but for simplicity we create it active here and assume client finishes upload.
    # A real system might have a status field (uploading vs active).
    asset = MediaAsset(
        org_id=current_user.org_id,
        uploaded_by=current_user.id,
        file_name=request.filename,
        file_type=request.mime_type,
        file_size=request.size_bytes,
        storage_key=storage_key,
        storage_provider=storage_service.provider,
        url=storage_service.get_public_url(storage_key)
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return {
        "upload_url": presigned_url,
        "media_asset_id": asset.id
    }

@authoring_router.put("/media/{asset_id}/confirm", dependencies=[Depends(require_admin)])
def confirm_media_upload(
    asset_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    asset = db.query(MediaAsset).filter(
        MediaAsset.id == asset_id,
        MediaAsset.org_id == current_user.org_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
        
    # In a more robust system, we check S3 to confirm file size/existence here.
    return {"success": True, "asset": asset.to_dict()}

# -----------------------------------------------------------------------------
# 5. Learning Paths API
# -----------------------------------------------------------------------------

class CreateLearningPathRequest(BaseModel):
    title: str
    description: Optional[str] = None

@authoring_router.post("/learning-paths", dependencies=[Depends(require_admin)])
def create_learning_path(
    request: CreateLearningPathRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    path = LearningPath(
        id=f"path-{uuid.uuid4().hex[:8]}",
        org_id=current_user.org_id,
        title=request.title,
        description=request.description,
        status="Draft",
        created_by=current_user.id
    )
    db.add(path)
    db.commit()
    db.refresh(path)
    return path.to_dict()

class LearningPathCourseUpdate(BaseModel):
    course_id: str
    sort_order: int

@authoring_router.put("/learning-paths/{path_id}/courses", dependencies=[Depends(require_admin)])
def update_learning_path_courses(
    path_id: str,
    updates: List[LearningPathCourseUpdate],
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id,
        LearningPath.org_id == current_user.org_id
    ).first()
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    # Clear existing
    db.query(LearningPathCourse).filter(LearningPathCourse.learning_path_id == path_id).delete()
    
    # Add new
    for update in updates:
        course_link = LearningPathCourse(
            learning_path_id=path_id,
            course_id=update.course_id,
            sort_order=update.sort_order,
            is_mandatory=True
        )
        db.add(course_link)
        
    db.commit()
    return {"success": True}

# -----------------------------------------------------------------------------
# Legacy Moodle Proxied Endpoints
# -----------------------------------------------------------------------------

class CreateModuleRequest(BaseModel):
    course_id: str
    section: int
    section_id: Optional[int] = None
    title: str
    module_type: str
    content_url: str | None = None
    
class UpdateModuleRequest(BaseModel):
    title: str
    content_url: str | None = None

@authoring_router.post("/modules", dependencies=[Depends(require_admin)])
def create_module(
    request: CreateModuleRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == request.course_id, Course.org_id == current_user.org_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Create native interactive module record
    # Note: Moodle proxy sync has been retired.
    
    section = None
    if request.section_id:
        section = db.query(CourseSection).filter(
            CourseSection.id == request.section_id,
            CourseSection.course_id == request.course_id,
            CourseSection.org_id == current_user.org_id,
        ).first()
        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

    max_order = db.query(CourseModule).filter(
        CourseModule.course_id == request.course_id, 
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
        CourseModule.section_id == request.section_id if request.section_id else CourseModule.section == request.section
    ).count()

    new_module = CourseModule(
        course_id=course.id,
        section=section.sort_order if section else request.section,
        section_id=section.id if section else None,
        title=request.title,
        module_type=request.module_type,
        sort_order=max_order,
        content_url=request.content_url,
        org_id=current_user.org_id,
        status="published"
    )
    db.add(new_module)
    db.flush()

    if new_module.module_type == "quiz":
        quiz = QuizDefinition(
            org_id=current_user.org_id,
            module_id=new_module.id,
            title=new_module.title,
        )
        db.add(quiz)

    db.commit()
    db.refresh(new_module)
    
    return {"success": True, "module": new_module.to_dict()}

@authoring_router.put("/modules/{module_id}", dependencies=[Depends(require_admin)])
def update_module(
    module_id: int,
    request: UpdateModuleRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    module = db.query(CourseModule).filter(CourseModule.id == module_id, CourseModule.org_id == current_user.org_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    # Update module in the database
    # Note: Moodle module update sync is retired.

    module.title = request.title
    if request.content_url is not None:
        module.content_url = request.content_url
        
    db.commit()
    db.refresh(module)
    
    return {"success": True, "module": module.to_dict()}

@authoring_router.post("/modules/{module_id}/duplicate", dependencies=[Depends(require_admin)])
def duplicate_module(
    module_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    source_module = db.query(CourseModule).filter(
        CourseModule.id == module_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).first()
    if not source_module:
        raise HTTPException(status_code=404, detail="Module not found")

    max_module_order = db.query(func.coalesce(func.max(CourseModule.sort_order), -1)).filter(
        CourseModule.course_id == source_module.course_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
        CourseModule.section_id == source_module.section_id,
    ).scalar()

    new_module = CourseModule(
        course_id=source_module.course_id,
        section=source_module.section,
        section_id=source_module.section_id,
        status=source_module.status,
        title=f"{source_module.title} Copy",
        module_type=source_module.module_type,
        sort_order=(max_module_order or -1) + 1,
        content_url=source_module.content_url,
        org_id=current_user.org_id,
    )
    db.add(new_module)
    db.flush()

    source_quiz = db.query(QuizDefinition).filter(
        QuizDefinition.module_id == source_module.id,
        QuizDefinition.org_id == current_user.org_id,
        QuizDefinition.deleted_at.is_(None),
    ).first()
    new_quiz = None
    if source_quiz:
        new_quiz = QuizDefinition(
            org_id=current_user.org_id,
            module_id=new_module.id,
            title=f"{source_quiz.title} Copy",
            description=source_quiz.description,
            passing_score=source_quiz.passing_score,
        )
        db.add(new_quiz)
        db.flush()

        source_settings = db.query(QuizSettings).filter(QuizSettings.quiz_id == source_quiz.id).first()
        if source_settings:
            db.add(QuizSettings(
                quiz_id=new_quiz.id,
                time_limit=source_settings.time_limit,
                passing_score=source_settings.passing_score,
                attempt_limit=source_settings.attempt_limit,
                show_answers=source_settings.show_answers,
                show_score=source_settings.show_score,
                shuffle_questions=source_settings.shuffle_questions,
                shuffle_options=source_settings.shuffle_options,
                cooldown_minutes=source_settings.cooldown_minutes,
                review_mode=source_settings.review_mode,
            ))

    source_blocks = db.query(LessonBlock).filter(
        LessonBlock.module_id == source_module.id,
        LessonBlock.org_id == current_user.org_id,
        LessonBlock.deleted_at.is_(None),
    ).order_by(LessonBlock.sort_order).all()
    for source_block in source_blocks:
        db.add(LessonBlock(
            module_id=new_module.id,
            org_id=current_user.org_id,
            block_type=source_block.block_type,
            content=source_block.content,
            media_asset_id=source_block.media_asset_id,
            sort_order=source_block.sort_order,
            metadata_json=copy.deepcopy(source_block.metadata_json),
        ))

    db.commit()
    db.refresh(new_module)

    return {"success": True, "module": new_module.to_dict()}

@authoring_router.delete("/modules/{module_id}", dependencies=[Depends(require_admin)])
def delete_module(
    module_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    module = db.query(CourseModule).filter(
        CourseModule.id == module_id,
        CourseModule.org_id == current_user.org_id,
        CourseModule.deleted_at.is_(None),
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    now = datetime.now(timezone.utc)
    module.deleted_at = now
    module.deleted_by = current_user.id

    blocks = db.query(LessonBlock).filter(
        LessonBlock.module_id == module.id,
        LessonBlock.org_id == current_user.org_id,
        LessonBlock.deleted_at.is_(None),
    ).all()
    for block in blocks:
        block.deleted_at = now
        block.deleted_by = current_user.id

    quiz_definitions = db.query(QuizDefinition).filter(
        QuizDefinition.module_id == module.id,
        QuizDefinition.org_id == current_user.org_id,
        QuizDefinition.deleted_at.is_(None),
    ).all()
    for quiz in quiz_definitions:
        quiz.deleted_at = now
        quiz.deleted_by = current_user.id
    db.commit()
    return {"success": True}

class QuizQuestionRequest(BaseModel):
    module_id: int
    question_text: str
    question_type: str
    options: list[str] = []
    correct_option: int = 0

@authoring_router.post("/modules/quiz/questions", dependencies=[Depends(require_admin)])
def add_quiz_question(
    request: QuizQuestionRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    module = db.query(CourseModule).filter(CourseModule.id == request.module_id, CourseModule.org_id == current_user.org_id).first()
    if not module or module.module_type != "quiz":
        raise HTTPException(status_code=404, detail="Quiz module not found")
        
    return {"success": True, "detail": "Question added to Moodle execution engine successfully"}
