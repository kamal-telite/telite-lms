from typing import Sequence, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.repositories.base_repo import BaseRepository
from app.models.question import Question, QuestionVersion

class QuestionRepository(BaseRepository[Question]):
    model = Question

    def get_with_versions(self, question_id: int, org_id: int) -> Optional[Question]:
        stmt = (
            select(Question)
            .options(joinedload(Question.versions))
            .where(Question.id == question_id, Question.org_id == org_id)
        )
        return self.session.execute(stmt).scalars().first()

class QuestionVersionRepository(BaseRepository[QuestionVersion]):
    model = QuestionVersion

    def get_latest_version_number(self, question_id: int, org_id: int) -> int:
        stmt = (
            select(QuestionVersion.version_number)
            .where(
                QuestionVersion.question_id == question_id,
                QuestionVersion.org_id == org_id
            )
            .order_by(QuestionVersion.version_number.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar()
        return result or 0
