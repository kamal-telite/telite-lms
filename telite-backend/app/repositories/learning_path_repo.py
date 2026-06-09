from __future__ import annotations
from typing import Sequence
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning_path import LearningPath, LearningPathCourse
from app.repositories.base_repo import BaseRepository
from app.models.builder_activity_log import BuilderActivityLog

class LearningPathRepository(BaseRepository):

    def get_paths(self, org_id: int) -> Sequence[LearningPath]:
        stmt = select(LearningPath).where(LearningPath.org_id == org_id, LearningPath.deleted_at.is_(None))
        return self.session.execute(stmt).scalars().all()

    def get_path(self, path_id: int, org_id: int) -> LearningPath | None:
        stmt = select(LearningPath).where(
            LearningPath.id == path_id,
            LearningPath.org_id == org_id,
            LearningPath.deleted_at.is_(None)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_path(self, org_id: int, title: str, description: str = "", settings: str = "{}") -> LearningPath:
        path = LearningPath(org_id=org_id, title=title, description=description, settings=settings)
        self.session.add(path)
        self.session.flush()
        return path

    def update_path(self, path: LearningPath, title: str, description: str, settings: str) -> None:
        path.title = title
        path.description = description
        path.settings = settings
        self.session.flush()

    def delete_path(self, path: LearningPath, user_id: str) -> None:
        path.deleted_at = datetime.now(timezone.utc)
        path.deleted_by = user_id
        self.session.flush()

    def get_path_courses(self, path_id: int) -> Sequence[LearningPathCourse]:
        stmt = select(LearningPathCourse).where(LearningPathCourse.path_id == path_id).order_by(LearningPathCourse.sort_order)
        return self.session.execute(stmt).scalars().all()

    def set_path_courses(self, path_id: int, course_ids: list[str]) -> None:
        # Delete existing
        self.session.query(LearningPathCourse).where(LearningPathCourse.path_id == path_id).delete()
        
        # Insert new
        for idx, cid in enumerate(course_ids):
            pc = LearningPathCourse(path_id=path_id, course_id=cid, sort_order=idx)
            self.session.add(pc)
            
        self.session.flush()

    def log_activity(self, path_id: int, user_id: str, org_id: int, action: str, payload: str = "{}") -> BuilderActivityLog:
        log = BuilderActivityLog(
            course_id=f"path_{path_id}",
            user_id=user_id,
            org_id=org_id,
            action=action,
            payload=payload
        )
        self.session.add(log)
        self.session.flush()
        return log
