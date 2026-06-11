from __future__ import annotations
import copy
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.course_module import CourseModule
from app.models.course_version import CourseVersion
from app.models.lesson_block import LessonBlock
from app.repositories.base_repo import BaseRepository
from app.models.builder_activity_log import BuilderActivityLog

class PublishingRepository(BaseRepository):

    def get_course(self, course_id: str, org_id: int) -> Course | None:
        stmt = select(Course).where(Course.id == course_id, Course.org_id == org_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_course_status(self, course: Course, status: str) -> None:
        course.status = status
        self.session.flush()

    def get_versions(self, course_id: str, org_id: int) -> Sequence[CourseVersion]:
        stmt = (
            select(CourseVersion)
            .where(CourseVersion.course_id == course_id, CourseVersion.org_id == org_id)
            .order_by(CourseVersion.version_number.desc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_version(self, version_id: int, org_id: int) -> CourseVersion | None:
        stmt = select(CourseVersion).where(
            CourseVersion.id == version_id, CourseVersion.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def create_version(
        self,
        course_id: str,
        org_id: int,
        version_number: int,
        parent_version_id: int | None = None,
        snapshot_json: dict | None = None,
    ) -> CourseVersion:
        version = CourseVersion(
            course_id=course_id,
            org_id=org_id,
            version_number=version_number,
            parent_version_id=parent_version_id,
            status="draft",
            snapshot_json=snapshot_json,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def build_snapshot(self, course_id: str, org_id: int) -> dict:
        course = self.get_course(course_id, org_id)
        if not course:
            raise ValueError("Course not found")

        sections = self.session.execute(
            select(CourseSection)
            .where(
                CourseSection.course_id == course_id,
                CourseSection.org_id == org_id,
                CourseSection.deleted_at.is_(None),
            )
            .order_by(CourseSection.sort_order, CourseSection.id)
        ).scalars().all()

        modules = self.session.execute(
            select(CourseModule)
            .where(
                CourseModule.course_id == course_id,
                CourseModule.org_id == org_id,
                CourseModule.deleted_at.is_(None),
            )
            .order_by(CourseModule.section_id, CourseModule.sort_order, CourseModule.id)
        ).scalars().all()

        module_ids = [module.id for module in modules]
        blocks = []
        if module_ids:
            blocks = self.session.execute(
                select(LessonBlock)
                .where(
                    LessonBlock.module_id.in_(module_ids),
                    LessonBlock.org_id == org_id,
                    LessonBlock.deleted_at.is_(None),
                )
                .order_by(LessonBlock.module_id, LessonBlock.sort_order, LessonBlock.id)
            ).scalars().all()

        blocks_by_module = {}
        for block in blocks:
            blocks_by_module.setdefault(block.module_id, []).append({
                "block_type": block.block_type,
                "content": block.content,
                "media_asset_id": block.media_asset_id,
                "sort_order": block.sort_order,
                "settings": copy.deepcopy(block.metadata_json or {}),
            })

        modules_by_section = {}
        for module in modules:
            modules_by_section.setdefault(module.section_id, []).append({
                "title": module.title,
                "module_type": module.module_type,
                "status": module.status,
                "content_url": module.content_url,
                "section": module.section,
                "sort_order": module.sort_order,
                "blocks": blocks_by_module.get(module.id, []),
            })

        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "course": {
                "id": course.id,
                "name": course.name,
                "status": course.status,
            },
            "sections": [
                {
                    "title": section.title,
                    "sort_order": section.sort_order,
                    "modules": modules_by_section.get(section.id, []),
                }
                for section in sections
            ],
        }

    def restore_snapshot(self, course_id: str, org_id: int, snapshot: dict, user_id: str) -> dict:
        course = self.get_course(course_id, org_id)
        if not course:
            raise ValueError("Course not found")

        now = datetime.now(timezone.utc)
        current_modules = self.session.execute(
            select(CourseModule).where(
                CourseModule.course_id == course_id,
                CourseModule.org_id == org_id,
                CourseModule.deleted_at.is_(None),
            )
        ).scalars().all()
        current_module_ids = [module.id for module in current_modules]

        if current_module_ids:
            blocks = self.session.execute(
                select(LessonBlock).where(
                    LessonBlock.module_id.in_(current_module_ids),
                    LessonBlock.org_id == org_id,
                    LessonBlock.deleted_at.is_(None),
                )
            ).scalars().all()
            for block in blocks:
                block.deleted_at = now
                block.deleted_by = user_id

        for module in current_modules:
            module.deleted_at = now
            module.deleted_by = user_id

        current_sections = self.session.execute(
            select(CourseSection).where(
                CourseSection.course_id == course_id,
                CourseSection.org_id == org_id,
                CourseSection.deleted_at.is_(None),
            )
        ).scalars().all()
        for section in current_sections:
            section.deleted_at = now
            section.deleted_by = user_id

        restored_sections = 0
        restored_modules = 0
        restored_blocks = 0
        for section_payload in snapshot.get("sections", []):
            section = CourseSection(
                course_id=course_id,
                org_id=org_id,
                title=section_payload.get("title") or "Untitled Section",
                sort_order=section_payload.get("sort_order") or restored_sections,
            )
            self.session.add(section)
            self.session.flush()
            restored_sections += 1

            for module_payload in section_payload.get("modules", []):
                module = CourseModule(
                    course_id=course_id,
                    org_id=org_id,
                    section=section.sort_order,
                    section_id=section.id,
                    status=module_payload.get("status") or "draft",
                    title=module_payload.get("title") or "Untitled Module",
                    module_type=module_payload.get("module_type") or "page",
                    sort_order=module_payload.get("sort_order") or restored_modules,
                    content_url=module_payload.get("content_url"),
                )
                self.session.add(module)
                self.session.flush()
                restored_modules += 1

                for block_payload in module_payload.get("blocks", []):
                    self.session.add(LessonBlock(
                        module_id=module.id,
                        org_id=org_id,
                        block_type=block_payload.get("block_type") or "text",
                        content=block_payload.get("content") or "",
                        media_asset_id=block_payload.get("media_asset_id"),
                        sort_order=block_payload.get("sort_order") or restored_blocks,
                        metadata_json=copy.deepcopy(block_payload.get("settings") or {}),
                    ))
                    restored_blocks += 1

        course.status = "draft"
        self.session.flush()
        return {
            "sections": restored_sections,
            "modules": restored_modules,
            "blocks": restored_blocks,
        }

    @staticmethod
    def snapshot_summary(snapshot: dict | None) -> dict:
        snapshot = snapshot or {}
        sections = snapshot.get("sections") or []
        modules = [module for section in sections for module in section.get("modules", [])]
        blocks = [block for module in modules for block in module.get("blocks", [])]
        return {"sections": len(sections), "modules": len(modules), "blocks": len(blocks)}

    def update_version_status(self, version: CourseVersion, status: str, user_id: str | None = None) -> None:
        version.status = status
        if status == "published" and user_id:
            version.published_by = user_id
            version.published_at = datetime.now(timezone.utc)
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
