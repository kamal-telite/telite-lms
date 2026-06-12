"""
Builder Repository for Native Course Builder.
Handles course sections, modules, lesson blocks, locks, and activity logs.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select

from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.course_edit_lock import CourseEditLock
from app.models.builder_activity_log import BuilderActivityLog
from app.repositories.base_repo import BaseRepository


class BuilderRepository(BaseRepository):
    # This repo handles multiple models, so we don't strict-bind 'model' class attribute
    
    def get_sections(self, course_id: str, org_id: int) -> Sequence[CourseSection]:
        stmt = (
            select(CourseSection)
            .where(
                CourseSection.course_id == course_id,
                CourseSection.org_id == org_id,
                CourseSection.deleted_at.is_(None),
            )
            .order_by(CourseSection.sort_order)
        )
        return self.session.execute(stmt).scalars().all()
        
    def get_modules(self, course_id: str, org_id: int) -> Sequence[CourseModule]:
        stmt = (
            select(CourseModule)
            .where(
                CourseModule.course_id == course_id,
                CourseModule.org_id == org_id,
                CourseModule.deleted_at.is_(None),
            )
            .order_by(CourseModule.sort_order)
        )
        return self.session.execute(stmt).scalars().all()

    def get_lock(self, course_id: str) -> CourseEditLock | None:
        stmt = select(CourseEditLock).where(CourseEditLock.course_id == course_id)
        return self.session.execute(stmt).scalar_one_or_none()
        
    def acquire_lock(self, course_id: str, user_id: str, org_id: int, expires_at: datetime) -> CourseEditLock:
        lock = self.get_lock(course_id)
        now = datetime.now(timezone.utc)
        if lock:
            lock.user_id = user_id
            lock.locked_at = now
            lock.expires_at = expires_at
        else:
            lock = CourseEditLock(
                course_id=course_id,
                user_id=user_id,
                locked_at=now,
                expires_at=expires_at,
                org_id=org_id
            )
            self.session.add(lock)
        self.session.flush()
        return lock
        
    def release_lock(self, lock: CourseEditLock) -> None:
        self.session.delete(lock)
        self.session.flush()

    def log_activity(self, course_id: str, user_id: str, org_id: int, action: str, payload: str = "{}") -> BuilderActivityLog:
        log = BuilderActivityLog(
            course_id=course_id,
            user_id=user_id,
            org_id=org_id,
            action=action,
            payload=payload
        )
        self.session.add(log)
        self.session.flush()
        return log

    def get_blocks(self, module_id: int, org_id: int) -> Sequence[LessonBlock]:
        stmt = (
            select(LessonBlock)
            .where(
                LessonBlock.module_id == module_id,
                LessonBlock.org_id == org_id,
                LessonBlock.deleted_at.is_(None),
            )
            .order_by(LessonBlock.sort_order)
        )
        return self.session.execute(stmt).scalars().all()

    def get_block_by_id(self, block_id: int, org_id: int) -> LessonBlock | None:
        stmt = select(LessonBlock).where(LessonBlock.id == block_id, LessonBlock.org_id == org_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def save_block(self, block: LessonBlock) -> LessonBlock:
        self.session.add(block)
        self.session.flush()
        return block

    def delete_block(self, block: LessonBlock, deleted_by: str | None = None) -> None:
        block.deleted_at = datetime.now(timezone.utc)
        block.deleted_by = deleted_by
        self.session.flush()
