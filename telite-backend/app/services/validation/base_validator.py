from typing import List
from sqlalchemy.orm import Session
from app.services.validation.schemas import ValidationResultItem

class BaseValidator:
    def __init__(self, db: Session, org_id: int):
        self.db = db
        self.org_id = org_id

    def validate(self, **kwargs) -> List[ValidationResultItem]:
        raise NotImplementedError("Subclasses must implement validate()")
