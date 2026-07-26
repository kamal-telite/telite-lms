from typing import Any

from app.models.question import Question, QuestionVersion
from app.models.question_category import QuestionCategory


def question_payload(q: Question, v: QuestionVersion, tag_ids: list[int]) -> dict:
    return {
        "id": q.id,
        "bank_id": q.bank_id,
        "category_id": v.category_id,
        "tag_ids": tag_ids,
        "current_draft_version_id": q.current_draft_version_id,
        "current_published_version_id": q.current_published_version_id,
        "question_type": v.question_type,
        "question_text": v.question_text,
        "points": v.points,
        "status": v.status,
        "version_state": v.status,
        "options_json": v.options_json,
        "correct_answer_json": v.correct_answer_json,
        "active_version_id": v.id,
        "version_number": v.version_number,
    }


def category_to_dict(category: QuestionCategory, children_by_parent: dict[int | None, list[QuestionCategory]]) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "parent_id": category.parent_id,
        "children": [
            category_to_dict(child, children_by_parent)
            for child in children_by_parent.get(category.id, [])
        ],
    }


def build_question_list_response(rows: list[tuple[Question, QuestionVersion]], tag_map: dict[int, list[int]], page: int, page_size: int, total: int) -> dict:
    return {
        "items": [question_payload(q, v, tag_map.get(v.id, [])) for q, v in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def build_question_version_payload(question: Question, version: QuestionVersion, version_tags: dict[int, list[int]]) -> dict:
    return {
        "id": version.id,
        "category_id": version.category_id,
        "tag_ids": version_tags.get(version.id, []),
        "status": version.status,
        "created_at": version.created_at,
        "question_type": version.question_type,
        "question_text": version.question_text,
        "points": version.points,
        "options_json": version.options_json,
        "correct_answer_json": version.correct_answer_json,
        "is_current_draft": version.id == question.current_draft_version_id,
        "is_current_published": version.id == question.current_published_version_id,
    }


def build_category_tree_response(categories: list[QuestionCategory], tree: bool) -> dict:
    if not tree:
        return {
            "items": [
                {"id": category.id, "name": category.name, "parent_id": category.parent_id}
                for category in categories
            ]
        }

    children_by_parent: dict[int | None, list[QuestionCategory]] = {}
    for category in categories:
        children_by_parent.setdefault(category.parent_id, []).append(category)
    return {
        "items": [
            category_to_dict(category, children_by_parent)
            for category in children_by_parent.get(None, [])
        ]
    }


def build_tag_list_response(tags: list[Any]) -> dict:
    return {"items": [{"id": tag.id, "name": tag.name} for tag in tags]}
