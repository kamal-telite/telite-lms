"""Progress Repository for fetching and updating learner course and module progress."""

from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_progress import CourseProgress
from app.models.module_progress import ModuleProgress
from app.models.lesson_block_progress import LessonBlockProgress
from app.models.section_progress import SectionProgress
from app.repositories.base_repo import BaseRepository


class ProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_course_progress(self, user_id: str, course_id: str, org_id: int) -> Optional[CourseProgress]:
        stmt = select(CourseProgress).where(
            CourseProgress.user_id == user_id,
            CourseProgress.course_id == course_id,
            CourseProgress.org_id == org_id
        ).order_by(CourseProgress.created_at.desc())
        result = self.session.execute(stmt).first()
        return result[0] if result else None

    def get_module_progress(self, user_id: str, module_id: int, org_id: int) -> Optional[ModuleProgress]:
        stmt = select(ModuleProgress).where(
            ModuleProgress.user_id == user_id,
            ModuleProgress.module_id == module_id,
            ModuleProgress.org_id == org_id
        ).order_by(ModuleProgress.created_at.desc())
        result = self.session.execute(stmt).first()
        return result[0] if result else None

    def get_section_progress(self, user_id: str, section_id: int, org_id: int) -> Optional[SectionProgress]:
        stmt = select(SectionProgress).where(
            SectionProgress.user_id == user_id,
            SectionProgress.section_id == section_id,
            SectionProgress.org_id == org_id
        ).order_by(SectionProgress.created_at.desc())
        result = self.session.execute(stmt).first()
        return result[0] if result else None

    def get_block_progress(self, user_id: str, block_id: str, org_id: int) -> Optional[LessonBlockProgress]:
        stmt = select(LessonBlockProgress).where(
            LessonBlockProgress.user_id == user_id,
            LessonBlockProgress.block_id == block_id,
            LessonBlockProgress.org_id == org_id
        ).order_by(LessonBlockProgress.created_at.desc())
        result = self.session.execute(stmt).first()
        return result[0] if result else None

    def upsert_course_progress(self, cp: CourseProgress) -> CourseProgress:
        self.session.add(cp)
        self.session.flush()
        return cp

    def upsert_module_progress(self, mp: ModuleProgress) -> ModuleProgress:
        self.session.add(mp)
        self.session.flush()
        return mp

    def upsert_section_progress(self, sp: SectionProgress) -> SectionProgress:
        self.session.add(sp)
        self.session.flush()
        return sp

    def upsert_block_progress(self, bp: LessonBlockProgress) -> LessonBlockProgress:
        self.session.add(bp)
        self.session.flush()
        return bp
