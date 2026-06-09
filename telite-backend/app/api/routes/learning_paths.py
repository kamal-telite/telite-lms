import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.repositories.learning_path_repo import LearningPathRepository
from app.repositories.publishing_repo import PublishingRepository

learning_paths_router = APIRouter(prefix="/authoring/learning-paths", tags=["Learning Paths API"])

# -----------------------------------------------------------------------------
# 1. Learning Path Builder
# -----------------------------------------------------------------------------

@learning_paths_router.get("", dependencies=[Depends(require_admin)])
def list_learning_paths(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    paths = repo.get_paths(current_user.org_id)
    return {"paths": [p.to_dict() for p in paths]}

class CreatePathRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    settings: Optional[Dict[str, Any]] = {}

@learning_paths_router.post("", dependencies=[Depends(require_admin)])
def create_learning_path(
    request: CreatePathRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    settings_str = json.dumps(request.settings)
    path = repo.create_path(current_user.org_id, request.title, request.description, settings_str)
    
    repo.log_activity(path.id, current_user.id, current_user.org_id, "PATH_CREATED", json.dumps({"title": path.title}))
    db.commit()
    return {"success": True, "path": path.to_dict()}

@learning_paths_router.get("/{path_id}", dependencies=[Depends(require_admin)])
def get_learning_path(
    path_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    path = repo.get_path(path_id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    courses = repo.get_path_courses(path_id)
    
    path_dict = path.to_dict()
    path_dict["settings"] = json.loads(path_dict["settings"])
    path_dict["courses"] = [c.to_dict() for c in courses]
    
    return {"path": path_dict}

@learning_paths_router.put("/{path_id}", dependencies=[Depends(require_admin)])
def update_learning_path(
    path_id: int,
    request: CreatePathRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    path = repo.get_path(path_id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    settings_str = json.dumps(request.settings)
    repo.update_path(path, request.title, request.description, settings_str)
    
    repo.log_activity(path.id, current_user.id, current_user.org_id, "PATH_UPDATED")
    db.commit()
    return {"success": True, "path": path.to_dict()}

@learning_paths_router.delete("/{path_id}", dependencies=[Depends(require_admin)])
def delete_learning_path(
    path_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    path = repo.get_path(path_id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    repo.delete_path(path, current_user.id)
    repo.log_activity(path.id, current_user.id, current_user.org_id, "PATH_DELETED")
    db.commit()
    return {"success": True}

# -----------------------------------------------------------------------------
# 2. Course Sequencing
# -----------------------------------------------------------------------------

class SequenceRequest(BaseModel):
    course_ids: List[str]

@learning_paths_router.post("/{path_id}/sequence", dependencies=[Depends(require_admin)])
def update_path_sequence(
    path_id: int,
    request: SequenceRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    path = repo.get_path(path_id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    repo.set_path_courses(path_id, request.course_ids)
    repo.log_activity(path.id, current_user.id, current_user.org_id, "PATH_SEQUENCE_UPDATED")
    db.commit()
    return {"success": True}

# -----------------------------------------------------------------------------
# 3. Path Analytics
# -----------------------------------------------------------------------------

@learning_paths_router.get("/{path_id}/analytics", dependencies=[Depends(require_admin)])
def get_path_analytics(
    path_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    repo = LearningPathRepository(db)
    path = repo.get_path(path_id, current_user.org_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
        
    # Simulated Analytics Engine
    return {
        "analytics": {
            "path_completion_percentage": 42.5,
            "total_enrolled": 150,
            "completed_learners": 63,
            "courses_stats": [
                {"course_id": "course-1", "completion_rate": 88.0, "is_bottleneck": False},
                {"course_id": "course-2", "completion_rate": 15.2, "is_bottleneck": True}
            ]
        }
    }
