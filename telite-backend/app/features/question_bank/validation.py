from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question_bank import QuestionBank
from app.models.question_category import QuestionCategory
from app.models.question_tag import QuestionTag


def normalize_version_status(value: str | None) -> str | None:
    return value.upper() if value else None


def validate_bank(db: Session, bank_id: int, org_id: int) -> QuestionBank:
    bank = db.execute(
        select(QuestionBank).where(QuestionBank.id == bank_id, QuestionBank.org_id == org_id)
    ).scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return bank


def validate_category(db: Session, category_id: int | None, org_id: int) -> QuestionCategory | None:
    if category_id is None:
        return None
    category = db.execute(
        select(QuestionCategory).where(
            QuestionCategory.id == category_id,
            QuestionCategory.org_id == org_id,
        )
    ).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=400, detail="Category not found or belongs to another tenant")
    return category


def validate_tags(db: Session, tag_ids: list[int], org_id: int) -> list[QuestionTag]:
    if not tag_ids:
        return []
    unique_ids = sorted(set(tag_ids))
    tags = db.execute(
        select(QuestionTag).where(
            QuestionTag.id.in_(unique_ids),
            QuestionTag.org_id == org_id,
        )
    ).scalars().all()
    if len(tags) != len(unique_ids):
        raise HTTPException(status_code=400, detail="One or more tags were not found or belong to another tenant")
    return tags


def validate_list_query_params(version_state: str | None, status_filter: str | None, sort_by: str, sort_order: str) -> tuple[str | None, dict[str, object]]:
    version_status = normalize_version_status(version_state or status_filter)
    if version_status and version_status not in {"DRAFT", "PUBLISHED", "ARCHIVED"}:
        raise HTTPException(status_code=400, detail="version_state/status must be DRAFT, PUBLISHED, or ARCHIVED")
    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_order must be asc or desc")

    sort_fields = {
        "updated_at": "updated_at",
        "created_at": "created_at",
        "question_text": "question_text",
        "version_number": "version_number",
        "id": "id",
    }
    if sort_by not in sort_fields:
        raise HTTPException(status_code=400, detail="sort_by must be one of: updated_at, created_at, question_text, version_number, id")
    return version_status, sort_fields
