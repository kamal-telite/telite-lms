"""
Builder Repository for Native Course Builder.
Handles course sections, modules, lesson blocks, locks, and activity logs.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Sequence
import logging
import time

from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.lesson_block import LessonBlock
from app.models.course_edit_lock import CourseEditLock
from app.models.builder_activity_log import BuilderActivityLog
from app.repositories.base_repo import BaseRepository

logger = logging.getLogger("telite.repositories.builder")


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
        logger.debug("Getting lock for course_id=%s", course_id)
        stmt = select(CourseEditLock).where(CourseEditLock.course_id == course_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        logger.debug("Lock query result: %s", result)
        return result

    def acquire_lock(self, course_id: str, user_id: str, org_id: int, expires_at: datetime) -> CourseEditLock:
        logger.debug("Acquiring lock for course_id=%s, user_id=%s, org_id=%s", course_id, user_id, org_id)
        now = datetime.now(timezone.utc)
        
        # Retry loop with exponential backoff to handle race conditions
        max_retries = 3
        base_delay = 0.05  # 50ms
        
        for attempt in range(max_retries):
            try:
                # Use atomic INSERT ... ON CONFLICT DO UPDATE to eliminate race condition
                # This handles both insert and update in a single database operation
                stmt = insert(CourseEditLock).values(
                    course_id=course_id,
                    user_id=user_id,
                    locked_at=now,
                    expires_at=expires_at,
                    org_id=org_id
                )
                
                # On conflict (course_id already exists), update the existing row
                stmt = stmt.on_conflict_do_update(
                    index_elements=['course_id'],
                    set_={
                        'user_id': user_id,
                        'locked_at': now,
                        'expires_at': expires_at
                    }
                )
                
                result = self.session.execute(stmt)
                self.session.flush()
                
                # Clear session state to prevent stale instances from causing StaleDataError
                self.session.expire_all()
                
                # Fetch and return the lock (whether it was inserted or updated)
                lock = self.get_lock(course_id)
                logger.debug("Lock acquired successfully (attempt %d): %s", attempt + 1, lock)
                return lock
                    
            except IntegrityError as e:
                # Duplicate key error - another request inserted the lock
                logger.warning("IntegrityError on attempt %d: %s", attempt + 1, str(e))
                self.session.rollback()
                from app.db.rls import set_rls_context
                set_rls_context(self.session, org_id)
                
                # If this is the last attempt, raise the error
                if attempt == max_retries - 1:
                    logger.error("Failed to acquire lock after %d retries", max_retries)
                    raise
                
                # Wait with exponential backoff before retrying
                delay = base_delay * (2 ** attempt)
                logger.debug("Retrying after %s seconds...", delay)
                time.sleep(delay)
        
        # This should never be reached, but just in case
        raise RuntimeError("Failed to acquire lock after retries")

    def release_lock(self, lock: CourseEditLock) -> None:
        self.session.delete(lock)
        self.session.flush()

    def log_activity(self, course_id: str, user_id: str, org_id: int, action: str, payload: str = "{}") -> BuilderActivityLog:
        logger.debug("Logging activity: course_id=%s, user_id=%s, action=%s", course_id, user_id, action)
        log = BuilderActivityLog(
            course_id=course_id,
            user_id=user_id,
            org_id=org_id,
            action=action,
            payload=payload
        )
        self.session.add(log)
        logger.debug("Flushing activity log to database")
        self.session.flush()
        logger.debug("Activity logged successfully")
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
        self._sync_media_usages(block)
        return block

    def _sync_media_usages(self, block: LessonBlock) -> None:
        from sqlalchemy import delete
        from app.models.media_asset_usage import MediaAssetUsage
        
        # Clear existing usages for this block
        self.session.execute(
            delete(MediaAssetUsage).where(
                MediaAssetUsage.entity_type == "lesson_block",
                MediaAssetUsage.entity_id == str(block.id),
                MediaAssetUsage.org_id == block.org_id
            )
        )
        
        usages_to_add = []
        
        # 1. Explicit foreign key
        if block.media_asset_id:
            usages_to_add.append(
                MediaAssetUsage(
                    media_asset_id=block.media_asset_id,
                    org_id=block.org_id,
                    entity_type="lesson_block",
                    entity_id=str(block.id),
                    usage_context="primary_asset"
                )
            )
            
        # 2. Known structured references in metadata_json
        if block.metadata_json:
            asset_id = block.metadata_json.get("asset_id")
            if asset_id and str(asset_id).isdigit():
                usages_to_add.append(
                    MediaAssetUsage(
                        media_asset_id=int(asset_id),
                        org_id=block.org_id,
                        entity_type="lesson_block",
                        entity_id=str(block.id),
                        usage_context="metadata_reference"
                    )
                )
        
        if usages_to_add:
            self.session.add_all(usages_to_add)
            self.session.flush()

    def delete_block(self, block: LessonBlock, deleted_by: str | None = None) -> None:
        block.deleted_at = datetime.now(timezone.utc)
        block.deleted_by = deleted_by
        self.session.flush()
