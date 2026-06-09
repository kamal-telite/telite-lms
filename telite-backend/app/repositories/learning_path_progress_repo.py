"""Learning Path Progress Repository."""

from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning_path_progress import LearningPathProgress


class LearningPathProgressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_progress(self, user_id: str, path_id: str, org_id: int) -> Optional[LearningPathProgress]:
        stmt = select(LearningPathProgress).where(
            LearningPathProgress.user_id == user_id,
            LearningPathProgress.path_id == path_id,
            LearningPathProgress.org_id == org_id
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_progress(self, progress: LearningPathProgress) -> LearningPathProgress:
        self.session.add(progress)
        self.session.flush()
        return progress
