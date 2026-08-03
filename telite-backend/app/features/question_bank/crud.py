from typing import Any
import logging

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DatabaseError

from app.models.question import Question, QuestionVersion
from app.models.question_category import QuestionCategory
from app.models.question_tag import QuestionTag, QuestionTagMap
from app.models.question_import_job import QuestionImportJob
from app.models.question_bank import QuestionBank
from app.features.question_bank.validation import validate_category, validate_tags, validate_list_query_params
from app.features.question_bank.utils import set_version_tags, tag_ids_for_versions
from app.features.question_bank.serializers import build_question_list_response, build_category_tree_response, build_tag_list_response
from app.services.question_bank_service import QuestionBankService

logger = logging.getLogger(__name__)


def list_questions(
    db: Session,
    org_id: int,
    *,
    bank_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    question_type: str | None = None,
    search: str | None = None,
    status_filter: str | None = None,
    version_state: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> dict:
    version_status, sort_fields = validate_list_query_params(version_state, status_filter, sort_by, sort_order)

    if tag_id is not None:
        validate_tags(db, [tag_id], org_id)
    validate_category(db, category_id, org_id)

    if version_status == "DRAFT":
        version_join = QuestionVersion.id == Question.current_draft_version_id
    elif version_status == "PUBLISHED":
        version_join = QuestionVersion.id == Question.current_published_version_id
    elif version_status == "ARCHIVED":
        version_join = (QuestionVersion.question_id == Question.id) & (QuestionVersion.status == "ARCHIVED")
    else:
        version_join = QuestionVersion.id == func.coalesce(
            Question.current_draft_version_id,
            Question.current_published_version_id,
        )

    stmt = (
        select(Question, QuestionVersion)
        .join(QuestionVersion, version_join)
        .where(Question.org_id == org_id, QuestionVersion.org_id == org_id)
    )
    if bank_id is not None:
        stmt = stmt.where(Question.bank_id == bank_id)
    if category_id is not None:
        stmt = stmt.where(QuestionVersion.category_id == category_id)
    if question_type:
        stmt = stmt.where(QuestionVersion.question_type == question_type)
    if version_status:
        stmt = stmt.where(QuestionVersion.status == version_status)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(QuestionVersion.question_text.ilike(term))
    if tag_id is not None:
        stmt = stmt.join(
            QuestionTagMap,
            (QuestionTagMap.question_version_id == QuestionVersion.id)
            & (QuestionTagMap.org_id == org_id)
            & (QuestionTagMap.tag_id == tag_id),
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    sort_expr = {
        "updated_at": func.coalesce(QuestionVersion.updated_at, QuestionVersion.created_at),
        "created_at": QuestionVersion.created_at,
        "question_text": QuestionVersion.question_text,
        "version_number": QuestionVersion.version_number,
        "id": Question.id,
    }[sort_by]
    order_expr = sort_expr.asc() if sort_order.lower() == "asc" else sort_expr.desc()
    rows = db.execute(
        stmt.order_by(order_expr, Question.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    tag_map = tag_ids_for_versions(db, org_id, [row[1].id for row in rows])
    return build_question_list_response(rows, tag_map, page, page_size, total)


def list_categories(db: Session, org_id: int, tree: bool = True) -> dict:
    categories = db.execute(
        select(QuestionCategory)
        .where(QuestionCategory.org_id == org_id)
        .order_by(QuestionCategory.parent_id.nullsfirst(), QuestionCategory.name)
    ).scalars().all()
    return build_category_tree_response(categories, tree)


def create_category(db: Session, org_id: int, req: Any) -> dict:
    try:
        if req.parent_id:
            validate_category(db, req.parent_id, org_id)
        cat = QuestionCategory(org_id=org_id, name=req.name, parent_id=req.parent_id)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        logger.info(
            "Category created successfully",
            extra={
                "category_id": cat.id,
                "org_id": org_id,
                "category_name": cat.name,
                "parent_id": cat.parent_id,
                "operation": "create_category"
            }
        )
        return {"id": cat.id, "name": cat.name, "parent_id": cat.parent_id}
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error creating category",
            extra={
                "org_id": org_id,
                "category_name": req.name,
                "parent_id": req.parent_id,
                "operation": "create_category",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Category name must be unique within organization") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error creating category",
            extra={
                "org_id": org_id,
                "category_name": req.name,
                "operation": "create_category",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create category due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating category",
            extra={
                "org_id": org_id,
                "category_name": req.name,
                "operation": "create_category",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create category") from e


def update_category(db: Session, org_id: int, category_id: int, req: Any) -> dict:
    try:
        category = db.execute(select(QuestionCategory).where(
            QuestionCategory.id == category_id,
            QuestionCategory.org_id == org_id,
        )).scalar_one_or_none()
        if not category:
            logger.warning(
                "Category not found for update",
                extra={
                    "category_id": category_id,
                    "org_id": org_id,
                    "operation": "update_category"
                }
            )
            raise HTTPException(status_code=404, detail="Category not found")

        updates = req.dict(exclude_unset=True)
        if "name" in updates and updates["name"]:
            category.name = updates["name"]
        if "parent_id" in updates:
            parent_id = updates["parent_id"]
            if parent_id == category.id:
                raise HTTPException(status_code=400, detail="Category cannot be its own parent")
            if parent_id is not None:
                parent = validate_category(db, parent_id, org_id)
                cursor = parent
                while cursor and cursor.parent_id is not None:
                    if cursor.parent_id == category.id:
                        raise HTTPException(status_code=400, detail="Category parent would create a cycle")
                    cursor = db.execute(select(QuestionCategory).where(
                        QuestionCategory.id == cursor.parent_id,
                        QuestionCategory.org_id == org_id,
                    )).scalar_one_or_none()
            category.parent_id = parent_id

        db.commit()
        db.refresh(category)
        logger.info(
            "Category updated successfully",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "update_category"
            }
        )
        return {"id": category.id, "name": category.name, "parent_id": category.parent_id}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error updating category",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "update_category",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Category name must be unique within organization") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error updating category",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "update_category",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update category due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error updating category",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "update_category",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update category") from e


def delete_category(db: Session, org_id: int, category_id: int) -> dict:
    try:
        category = db.execute(select(QuestionCategory).where(
            QuestionCategory.id == category_id,
            QuestionCategory.org_id == org_id,
        )).scalar_one_or_none()
        if not category:
            logger.warning(
                "Category not found for deletion",
                extra={
                    "category_id": category_id,
                    "org_id": org_id,
                    "operation": "delete_category"
                }
            )
            raise HTTPException(status_code=404, detail="Category not found")

        question_count = db.execute(select(func.count()).select_from(QuestionVersion).where(
            QuestionVersion.category_id == category_id,
            QuestionVersion.org_id == org_id,
        )).scalar_one()
        child_count = db.execute(select(func.count()).select_from(QuestionCategory).where(
            QuestionCategory.parent_id == category_id,
            QuestionCategory.org_id == org_id,
        )).scalar_one()
        if question_count or child_count:
            logger.warning(
                "Category deletion blocked - in use",
                extra={
                    "category_id": category_id,
                    "org_id": org_id,
                    "question_count": question_count,
                    "child_count": child_count,
                    "operation": "delete_category"
                }
            )
            raise HTTPException(
                status_code=409,
                detail="Category is in use by questions or child categories and cannot be deleted",
            )

        db.delete(category)
        db.commit()
        logger.info(
            "Category deleted successfully",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "delete_category"
            }
        )
        return {"success": True}
    except HTTPException:
        db.rollback()
        raise
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error deleting category",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "delete_category",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to delete category due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error deleting category",
            extra={
                "category_id": category_id,
                "org_id": org_id,
                "operation": "delete_category",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to delete category") from e


def list_tags(db: Session, org_id: int) -> dict:
    tags = db.execute(
        select(QuestionTag)
        .where(QuestionTag.org_id == org_id)
        .order_by(QuestionTag.name)
    ).scalars().all()
    return build_tag_list_response(tags)


def create_tag(db: Session, org_id: int, req: Any) -> dict:
    try:
        tag = QuestionTag(org_id=org_id, name=req.name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
        logger.info(
            "Tag created successfully",
            extra={
                "tag_id": tag.id,
                "org_id": org_id,
                "tag_name": tag.name,
                "operation": "create_tag"
            }
        )
        return {"id": tag.id, "name": tag.name}
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error creating tag",
            extra={
                "org_id": org_id,
                "tag_name": req.name,
                "operation": "create_tag",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Tag name must be unique within organization") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error creating tag",
            extra={
                "org_id": org_id,
                "tag_name": req.name,
                "operation": "create_tag",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create tag due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating tag",
            extra={
                "org_id": org_id,
                "tag_name": req.name,
                "operation": "create_tag",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create tag") from e


def update_tag(db: Session, org_id: int, tag_id: int, req: Any) -> dict:
    try:
        tag = db.execute(select(QuestionTag).where(
            QuestionTag.id == tag_id,
            QuestionTag.org_id == org_id,
        )).scalar_one_or_none()
        if not tag:
            logger.warning(
                "Tag not found for update",
                extra={
                    "tag_id": tag_id,
                    "org_id": org_id,
                    "operation": "update_tag"
                }
            )
            raise HTTPException(status_code=404, detail="Tag not found")
        tag.name = req.name
        db.commit()
        db.refresh(tag)
        logger.info(
            "Tag updated successfully",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "update_tag"
            }
        )
        return {"id": tag.id, "name": tag.name}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error updating tag",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "update_tag",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Tag name must be unique within organization") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error updating tag",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "update_tag",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update tag due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error updating tag",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "update_tag",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update tag") from e


def delete_tag(db: Session, org_id: int, tag_id: int) -> dict:
    try:
        tag = db.execute(select(QuestionTag).where(
            QuestionTag.id == tag_id,
            QuestionTag.org_id == org_id,
        )).scalar_one_or_none()
        if not tag:
            logger.warning(
                "Tag not found for deletion",
                extra={
                    "tag_id": tag_id,
                    "org_id": org_id,
                    "operation": "delete_tag"
                }
            )
            raise HTTPException(status_code=404, detail="Tag not found")

        usage_count = db.execute(select(func.count()).select_from(QuestionTagMap).where(
            QuestionTagMap.tag_id == tag_id,
            QuestionTagMap.org_id == org_id,
        )).scalar_one()
        if usage_count:
            logger.warning(
                "Tag deletion blocked - in use",
                extra={
                    "tag_id": tag_id,
                    "org_id": org_id,
                    "usage_count": usage_count,
                    "operation": "delete_tag"
                }
            )
            raise HTTPException(status_code=409, detail="Tag is in use by questions and cannot be deleted")

        db.delete(tag)
        db.commit()
        logger.info(
            "Tag deleted successfully",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "delete_tag"
            }
        )
        return {"success": True}
    except HTTPException:
        db.rollback()
        raise
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error deleting tag",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "delete_tag",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to delete tag due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error deleting tag",
            extra={
                "tag_id": tag_id,
                "org_id": org_id,
                "operation": "delete_tag",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to delete tag") from e


def create_question(db: Session, org_id: int, bank_id: int, req: Any) -> dict:
    try:
        validate_category(db, req.category_id, org_id)
        validate_tags(db, req.tag_ids, org_id)
        svc = QuestionBankService(db)
        q = svc.create_question(
            org_id=org_id,
            bank_id=bank_id,
            category_id=req.category_id,
            question_type=req.question_type,
            question_text=req.question_text,
            points=req.points,
            options_json=req.options_json,
            correct_answer_json=req.correct_answer_json,
        )
        if q.current_draft_version_id:
            set_version_tags(db, q.current_draft_version_id, org_id, req.tag_ids)
        db.commit()
        logger.info(
            "Question created successfully",
            extra={
                "question_id": q.id,
                "org_id": org_id,
                "bank_id": bank_id,
                "category_id": req.category_id,
                "question_type": req.question_type,
                "operation": "create_question"
            }
        )
        return {"id": q.id, "current_draft_version_id": q.current_draft_version_id, "category_id": q.category_id, "tag_ids": req.tag_ids}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error creating question",
            extra={
                "org_id": org_id,
                "bank_id": bank_id,
                "category_id": req.category_id,
                "question_type": req.question_type,
                "operation": "create_question",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Question creation failed due to database constraint violation") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error creating question",
            extra={
                "org_id": org_id,
                "bank_id": bank_id,
                "category_id": req.category_id,
                "question_type": req.question_type,
                "operation": "create_question",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create question due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating question",
            extra={
                "org_id": org_id,
                "bank_id": bank_id,
                "category_id": req.category_id,
                "question_type": req.question_type,
                "operation": "create_question",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create question") from e


def update_draft_question(db: Session, org_id: int, bank_id: int, q_id: int, req: Any) -> dict:
    try:
        svc = QuestionBankService(db)
        question = svc.question_repo.get_by_id_and_org(q_id, org_id)
        if not question or question.bank_id != bank_id:
            logger.warning(
                "Question not found for draft update",
                extra={
                    "question_id": q_id,
                    "org_id": org_id,
                    "bank_id": bank_id,
                    "operation": "update_draft_question"
                }
            )
            raise HTTPException(status_code=404, detail="Question not found")

        if not question.current_draft_version_id:
            logger.warning(
                "No active draft exists for question",
                extra={
                    "question_id": q_id,
                    "org_id": org_id,
                    "operation": "update_draft_question"
                }
            )
            raise HTTPException(
                status_code=400,
                detail="No active draft exists. Create a new draft from the published version first.",
            )

        draft = svc.version_repo.get_by_id_and_org(question.current_draft_version_id, org_id)
        if not draft or draft.status != "DRAFT":
            logger.warning(
                "Invalid draft state for question",
                extra={
                    "question_id": q_id,
                    "draft_version_id": question.current_draft_version_id,
                    "org_id": org_id,
                    "operation": "update_draft_question"
                }
            )
            raise HTTPException(status_code=400, detail="Invalid draft state")

        updates = req.model_dump(exclude_unset=True)
        tag_ids = updates.pop("tag_ids", None)
        category_id = updates.pop("category_id", None)
        if "category_id" in req.model_fields_set:
            validate_category(db, category_id, org_id)
            svc.question_repo.update(question, category_id=category_id)
            svc.version_repo.update(draft, category_id=category_id)
        if tag_ids is not None:
            set_version_tags(db, draft.id, org_id, tag_ids)
        svc.version_repo.update(draft, **updates)
        db.commit()
        logger.info(
            "Draft question updated successfully",
            extra={
                "question_id": q_id,
                "draft_version_id": draft.id,
                "org_id": org_id,
                "operation": "update_draft_question"
            }
        )
        return {"id": q_id, "draft_version_id": draft.id, "status": "updated", "category_id": draft.category_id, "tag_ids": tag_ids}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error updating draft question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "update_draft_question",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Question update failed due to database constraint violation") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error updating draft question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "update_draft_question",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update question due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error updating draft question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "update_draft_question",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to update question") from e


def publish_question(db: Session, org_id: int, q_id: int) -> dict:
    try:
        svc = QuestionBankService(db)
        published_version = svc.publish_question(org_id, q_id)
        db.commit()
        logger.info(
            "Question published successfully",
            extra={
                "question_id": q_id,
                "published_version_id": published_version.id,
                "org_id": org_id,
                "operation": "publish_question"
            }
        )
        return {"id": q_id, "published_version_id": published_version.id, "status": "published"}
    except ValueError as e:
        db.rollback()
        logger.warning(
            "Business logic error publishing question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "error_message": str(e),
                "operation": "publish_question"
            }
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error publishing question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "publish_question",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Question publish failed due to database constraint violation") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error publishing question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "publish_question",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to publish question due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error publishing question",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "publish_question",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to publish question") from e


def create_new_draft_from_published(db: Session, org_id: int, bank_id: int, q_id: int) -> dict:
    try:
        svc = QuestionBankService(db)
        question = svc.question_repo.get_by_id_and_org(q_id, org_id)
        if not question or question.bank_id != bank_id:
            logger.warning(
                "Question not found for draft creation",
                extra={
                    "question_id": q_id,
                    "org_id": org_id,
                    "bank_id": bank_id,
                    "operation": "create_new_draft_from_published"
                }
            )
            raise HTTPException(status_code=404, detail="Question not found")
        published_version_id = question.current_published_version_id
        new_version = svc.edit_published_question(org_id, q_id, updates={})
        if published_version_id:
            published_tags = tag_ids_for_versions(db, org_id, [published_version_id])
            set_version_tags(
                db,
                new_version.id,
                org_id,
                published_tags.get(published_version_id, []),
            )
        db.commit()
        logger.info(
            "New draft created from published question successfully",
            extra={
                "question_id": q_id,
                "draft_version_id": new_version.id,
                "published_version_id": published_version_id,
                "org_id": org_id,
                "operation": "create_new_draft_from_published"
            }
        )
        return {"id": q_id, "draft_version_id": new_version.id, "status": "draft_created"}
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        logger.warning(
            "Business logic error creating draft from published",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "error_message": str(e),
                "operation": "create_new_draft_from_published"
            }
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error creating draft from published",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "create_new_draft_from_published",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Draft creation failed due to database constraint violation") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error creating draft from published",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "create_new_draft_from_published",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create draft due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating draft from published",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "create_new_draft_from_published",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create draft") from e


def archive_draft_question(db: Session, org_id: int, q_id: int) -> dict:
    try:
        svc = QuestionBankService(db)
        svc.archive_draft(org_id, q_id)
        db.commit()
        logger.info(
            "Draft question archived successfully",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "archive_draft_question"
            }
        )
        return {"status": "archived"}
    except ValueError as e:
        db.rollback()
        logger.warning(
            "Business logic error archiving draft",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "error_message": str(e),
                "operation": "archive_draft_question"
            }
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error archiving draft",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "archive_draft_question",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to archive draft due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error archiving draft",
            extra={
                "question_id": q_id,
                "org_id": org_id,
                "operation": "archive_draft_question",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to archive draft") from e


def get_question_versions(db: Session, org_id: int, bank_id: int, q_id: int) -> list[dict]:
    svc = QuestionBankService(db)
    question = svc.question_repo.get_by_id_and_org(q_id, org_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    versions = db.execute(
        select(QuestionVersion).where(QuestionVersion.question_id == q_id).order_by(QuestionVersion.created_at.desc())
    ).scalars().all()
    version_tags = tag_ids_for_versions(db, org_id, [v.id for v in versions])

    return [
        {
            "id": v.id,
            "category_id": v.category_id,
            "tag_ids": version_tags.get(v.id, []),
            "status": v.status,
            "created_at": v.created_at,
            "question_type": v.question_type,
            "question_text": v.question_text,
            "points": v.points,
            "options_json": v.options_json,
            "correct_answer_json": v.correct_answer_json,
            "is_current_draft": v.id == question.current_draft_version_id,
            "is_current_published": v.id == question.current_published_version_id,
        }
        for v in versions
    ]


def create_import_job(db: Session, org_id: int, user_id: int, req: Any) -> dict:
    try:
        import uuid

        validate_category(db, req.category_id, org_id)
        validate_tags(db, req.tag_ids, org_id)
        metadata = {
            "file_key": req.file_key,
            "category_id": req.category_id,
            "tag_ids": sorted(set(req.tag_ids)),
        }
        job = QuestionImportJob(
            id=uuid.uuid4().hex,
            org_id=org_id,
            user_id=user_id,
            status="UPLOADED",
            error_log=None,
            metadata_json=metadata,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(
            "Import job created successfully",
            extra={
                "job_id": job.id,
                "org_id": org_id,
                "user_id": user_id,
                "category_id": req.category_id,
                "operation": "create_import_job"
            }
        )
        return {"id": job.id, "status": job.status, "metadata_json": job.metadata_json}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(
            "Database integrity error creating import job",
            extra={
                "org_id": org_id,
                "user_id": user_id,
                "category_id": req.category_id,
                "operation": "create_import_job",
                "error_type": "IntegrityError"
            }
        )
        raise HTTPException(status_code=409, detail="Import job creation failed due to database constraint violation") from e
    except DatabaseError as e:
        db.rollback()
        logger.error(
            "Database error creating import job",
            extra={
                "org_id": org_id,
                "user_id": user_id,
                "category_id": req.category_id,
                "operation": "create_import_job",
                "error_type": "DatabaseError"
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create import job due to database error") from e
    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating import job",
            extra={
                "org_id": org_id,
                "user_id": user_id,
                "category_id": req.category_id,
                "operation": "create_import_job",
                "error_type": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create import job") from e


def check_stale_versions(db: Session, org_id: int, req: Any) -> dict:
    result = {}
    for item in req.items:
        q_id = item.get("question_id")
        v_id = item.get("version_id")
        if not q_id or not v_id:
            continue

        q = db.execute(select(Question).where(Question.id == q_id, Question.org_id == org_id)).scalar_one_or_none()
        if q and q.current_published_version_id and q.current_published_version_id != v_id:
            result[q_id] = {
                "is_stale": True,
                "latest_version_id": q.current_published_version_id,
            }
        else:
            result[q_id] = {
                "is_stale": False,
                "latest_version_id": q.current_published_version_id if q else None,
            }

    return result
