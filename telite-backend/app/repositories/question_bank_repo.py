from typing import Sequence
from sqlalchemy import select
from app.repositories.base_repo import BaseRepository
from app.models.question_bank import QuestionBank

class QuestionBankRepository(BaseRepository[QuestionBank]):
    model = QuestionBank

    def get_by_id_and_org(self, bank_id: int, org_id: int) -> QuestionBank | None:
        return super().get_by_id_and_org(bank_id, org_id)
