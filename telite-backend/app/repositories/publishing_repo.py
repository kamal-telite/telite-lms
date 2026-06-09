from __future__ import annotations
from typing import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_version import CourseVersion
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
        self, course_id: str, org_id: int, version_number: int, parent_version_id: int | None = None
    ) -> CourseVersion:
        version = CourseVersion(
            course_id=course_id,
            org_id=org_id,
            version_number=version_number,
            parent_version_id=parent_version_id,
            status="draft"
        )
        self.session.add(version)
        self.session.flush()
        return version

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
