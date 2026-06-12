"""Progress Repository for fetching and updating learner course and module progress."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.lesson_block_progress import LessonBlockProgress


class ProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_course_progress(self, user_id: str, course_id: str, org_id: int) -> Optional[CourseProgress]:
        stmt = select(CourseProgress).where(
            CourseProgress.user_id == user_id,
            CourseProgress.course_id == course_id,
            CourseProgress.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_module_progress(self, user_id: str, module_id: int, org_id: int) -> Optional[ModuleProgress]:
        stmt = select(ModuleProgress).where(
            ModuleProgress.user_id == user_id,
            ModuleProgress.module_id == module_id,
            ModuleProgress.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_block_progress(self, user_id: str, block_id: str, org_id: int) -> Optional[LessonBlockProgress]:
        stmt = select(LessonBlockProgress).where(
            LessonBlockProgress.user_id == user_id,
            LessonBlockProgress.block_id == block_id,
            LessonBlockProgress.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_course_progress(self, cp: CourseProgress) -> CourseProgress:
        self.session.add(cp)
        self.session.flush()
        return cp

    def upsert_module_progress(self, mp: ModuleProgress) -> ModuleProgress:
        self.session.add(mp)
        self.session.flush()
        return mp

    def upsert_block_progress(self, bp: LessonBlockProgress) -> LessonBlockProgress:
        self.session.add(bp)
        self.session.flush()
        return bp
