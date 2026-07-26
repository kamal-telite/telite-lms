from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question_tag import QuestionTagMap
from app.features.question_bank.validation import validate_tags


def set_version_tags(db: Session, version_id: int, org_id: int, tag_ids: list[int]) -> None:
    validate_tags(db, tag_ids, org_id)
    existing = db.execute(
        select(QuestionTagMap).where(
            QuestionTagMap.question_version_id == version_id,
            QuestionTagMap.org_id == org_id,
        )
    ).scalars().all()
    for item in existing:
        db.delete(item)
    for tag_id in sorted(set(tag_ids)):
        db.add(QuestionTagMap(org_id=org_id, question_version_id=version_id, tag_id=tag_id))


def tag_ids_for_versions(db: Session, org_id: int, version_ids: list[int]) -> dict[int, list[int]]:
    if not version_ids:
        return {}
    rows = db.execute(
        select(QuestionTagMap.question_version_id, QuestionTagMap.tag_id).where(
            QuestionTagMap.org_id == org_id,
            QuestionTagMap.question_version_id.in_(version_ids),
        )
    ).all()
    result: dict[int, list[int]] = {}
    for version_id, tag_id in rows:
        result.setdefault(version_id, []).append(tag_id)
    return result
