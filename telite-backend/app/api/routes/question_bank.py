from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_, select

from app.api.auth import get_current_user, TokenData
from app.core.rbac import require_permission, Permission
from app.db.engine import db_session
from app.services.question_bank_service import QuestionBankService
from app.models.question_bank import QuestionBank
from app.models.question import Question, QuestionVersion
from app.models.question_category import QuestionCategory
from app.models.question_tag import QuestionTag, QuestionTagMap
from app.models.question_import_job import QuestionImportJob

question_bank_router = APIRouter(tags=["Question Bank"])

# --- Schemas ---

class QuestionBankCreate(BaseModel):
    name: str

class QuestionBankResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    category_id: Optional[int] = None
    tag_ids: List[int] = []
    question_type: str
    question_text: str
    points: int = 1
    options_json: List[Dict[str, Any]] = []
    correct_answer_json: List[str] = []

class QuestionUpdateDraft(BaseModel):
    category_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    points: Optional[int] = None
    options_json: Optional[List[Dict[str, Any]]] = None
    correct_answer_json: Optional[List[str]] = None

class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None

class TagCreate(BaseModel):
    name: str

class TagUpdate(BaseModel):
    name: str

class ImportJobCreate(BaseModel):
    file_key: str
    category_id: Optional[int] = None
    tag_ids: List[int] = []


def _normalize_version_status(value: str | None) -> str | None:
    return value.upper() if value else None


def _validate_bank(db: Session, bank_id: int, org_id: int) -> QuestionBank:
    bank = db.execute(
        select(QuestionBank).where(QuestionBank.id == bank_id, QuestionBank.org_id == org_id)
    ).scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return bank


def _validate_category(db: Session, category_id: int | None, org_id: int) -> QuestionCategory | None:
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


def _validate_tags(db: Session, tag_ids: list[int], org_id: int) -> list[QuestionTag]:
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


def _set_version_tags(db: Session, version_id: int, org_id: int, tag_ids: list[int]) -> None:
    _validate_tags(db, tag_ids, org_id)
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


def _tag_ids_for_versions(db: Session, org_id: int, version_ids: list[int]) -> dict[int, list[int]]:
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


def _question_payload(q: Question, v: QuestionVersion, tag_ids: list[int]) -> dict:
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


def _list_questions(
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
    version_status = _normalize_version_status(version_state or status_filter)
    if version_status and version_status not in {"DRAFT", "PUBLISHED", "ARCHIVED"}:
        raise HTTPException(status_code=400, detail="version_state/status must be DRAFT, PUBLISHED, or ARCHIVED")
    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="sort_order must be asc or desc")

    sort_fields = {
        "updated_at": func.coalesce(QuestionVersion.updated_at, QuestionVersion.created_at),
        "created_at": QuestionVersion.created_at,
        "question_text": QuestionVersion.question_text,
        "version_number": QuestionVersion.version_number,
        "id": Question.id,
    }
    if sort_by not in sort_fields:
        raise HTTPException(status_code=400, detail="sort_by must be one of: updated_at, created_at, question_text, version_number, id")

    if tag_id is not None:
        _validate_tags(db, [tag_id], org_id)
    _validate_category(db, category_id, org_id)

    if version_status == "DRAFT":
        version_join = QuestionVersion.id == Question.current_draft_version_id
    elif version_status == "PUBLISHED":
        version_join = QuestionVersion.id == Question.current_published_version_id
    elif version_status == "ARCHIVED":
        version_join = and_(QuestionVersion.question_id == Question.id, QuestionVersion.status == "ARCHIVED")
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
            and_(
                QuestionTagMap.question_version_id == QuestionVersion.id,
                QuestionTagMap.org_id == org_id,
                QuestionTagMap.tag_id == tag_id,
            ),
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    sort_expr = sort_fields[sort_by]
    order_expr = sort_expr.asc() if sort_order.lower() == "asc" else sort_expr.desc()
    rows = db.execute(
        stmt.order_by(order_expr, Question.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    ).all()
    tag_map = _tag_ids_for_versions(db, org_id, [row[1].id for row in rows])
    return {
        "items": [_question_payload(q, v, tag_map.get(v.id, [])) for q, v in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def _category_to_dict(category: QuestionCategory, children_by_parent: dict[int | None, list[QuestionCategory]]) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "parent_id": category.parent_id,
        "children": [
            _category_to_dict(child, children_by_parent)
            for child in children_by_parent.get(category.id, [])
        ],
    }


def _list_categories_response(db: Session, org_id: int, tree: bool = True) -> dict:
    categories = db.execute(
        select(QuestionCategory)
        .where(QuestionCategory.org_id == org_id)
        .order_by(QuestionCategory.parent_id.nullsfirst(), QuestionCategory.name)
    ).scalars().all()
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
            _category_to_dict(category, children_by_parent)
            for category in children_by_parent.get(None, [])
        ]
    }


def _create_category_response(db: Session, org_id: int, req: CategoryCreate) -> dict:
    if req.parent_id:
        _validate_category(db, req.parent_id, org_id)
    cat = QuestionCategory(org_id=org_id, name=req.name, parent_id=req.parent_id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "parent_id": cat.parent_id}


def _update_category_response(db: Session, org_id: int, category_id: int, req: CategoryUpdate) -> dict:
    category = db.execute(select(QuestionCategory).where(
        QuestionCategory.id == category_id,
        QuestionCategory.org_id == org_id,
    )).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = req.dict(exclude_unset=True)
    if "name" in updates and updates["name"]:
        category.name = updates["name"]
    if "parent_id" in updates:
        parent_id = updates["parent_id"]
        if parent_id == category.id:
            raise HTTPException(status_code=400, detail="Category cannot be its own parent")
        if parent_id is not None:
            parent = _validate_category(db, parent_id, org_id)
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
    return {"id": category.id, "name": category.name, "parent_id": category.parent_id}


def _delete_category_response(db: Session, org_id: int, category_id: int) -> dict:
    category = db.execute(select(QuestionCategory).where(
        QuestionCategory.id == category_id,
        QuestionCategory.org_id == org_id,
    )).scalar_one_or_none()
    if not category:
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
        raise HTTPException(
            status_code=409,
            detail="Category is in use by questions or child categories and cannot be deleted",
        )

    db.delete(category)
    db.commit()
    return {"success": True}


def _list_tags_response(db: Session, org_id: int) -> dict:
    tags = db.execute(
        select(QuestionTag)
        .where(QuestionTag.org_id == org_id)
        .order_by(QuestionTag.name)
    ).scalars().all()
    return {"items": [{"id": tag.id, "name": tag.name} for tag in tags]}


def _create_tag_response(db: Session, org_id: int, req: TagCreate) -> dict:
    tag = QuestionTag(org_id=org_id, name=req.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name}


def _update_tag_response(db: Session, org_id: int, tag_id: int, req: TagUpdate) -> dict:
    tag = db.execute(select(QuestionTag).where(
        QuestionTag.id == tag_id,
        QuestionTag.org_id == org_id,
    )).scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag.name = req.name
    db.commit()
    db.refresh(tag)
    return {"id": tag.id, "name": tag.name}


def _delete_tag_response(db: Session, org_id: int, tag_id: int) -> dict:
    tag = db.execute(select(QuestionTag).where(
        QuestionTag.id == tag_id,
        QuestionTag.org_id == org_id,
    )).scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    usage_count = db.execute(select(func.count()).select_from(QuestionTagMap).where(
        QuestionTagMap.tag_id == tag_id,
        QuestionTagMap.org_id == org_id,
    )).scalar_one()
    if usage_count:
        raise HTTPException(status_code=409, detail="Tag is in use by questions and cannot be deleted")

    db.delete(tag)
    db.commit()
    return {"success": True}

# --- Question Bank Endpoints ---

@question_bank_router.post("/question-banks", response_model=QuestionBankResponse)
def create_question_bank(
    req: QuestionBankCreate,
    current_user: TokenData = Depends(require_permission(Permission.ORG_MANAGE_BANKS)),
    db: Session = Depends(db_session)
):
    bank = QuestionBank(org_id=current_user.org_id, name=req.name)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank

@question_bank_router.get("/question-banks", response_model=List[QuestionBankResponse])
def list_question_banks(
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    stmt = select(QuestionBank).where(QuestionBank.org_id == current_user.org_id)
    return db.execute(stmt).scalars().all()

@question_bank_router.get("/question-banks/questions")
def list_all_questions(
    bank_id: Optional[int] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    tag_id: Optional[int] = Query(default=None),
    question_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    version_state: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    if bank_id is not None:
        _validate_bank(db, bank_id, current_user.org_id)
    return _list_questions(
        db,
        current_user.org_id,
        bank_id=bank_id,
        category_id=category_id,
        tag_id=tag_id,
        question_type=question_type,
        search=search,
        status_filter=status,
        version_state=version_state,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@question_bank_router.get("/question-banks/categories")
def list_categories_route(
    tree: bool = Query(default=True),
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _list_categories_response(db, current_user.org_id, tree)

@question_bank_router.post("/question-banks/categories")
def create_category_route(
    req: CategoryCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _create_category_response(db, current_user.org_id, req)

@question_bank_router.put("/question-banks/categories/{category_id}")
def update_category_route(
    category_id: int,
    req: CategoryUpdate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _update_category_response(db, current_user.org_id, category_id, req)

@question_bank_router.delete("/question-banks/categories/{category_id}")
def delete_category_route(
    category_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _delete_category_response(db, current_user.org_id, category_id)

@question_bank_router.get("/question-banks/tags")
def list_tags_route(
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _list_tags_response(db, current_user.org_id)

@question_bank_router.post("/question-banks/tags")
def create_tag_route(
    req: TagCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _create_tag_response(db, current_user.org_id, req)

@question_bank_router.put("/question-banks/tags/{tag_id}")
def update_tag_route(
    tag_id: int,
    req: TagUpdate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _update_tag_response(db, current_user.org_id, tag_id, req)

@question_bank_router.delete("/question-banks/tags/{tag_id}")
def delete_tag_route(
    tag_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    return _delete_tag_response(db, current_user.org_id, tag_id)

@question_bank_router.get("/question-banks/{bank_id}", response_model=QuestionBankResponse)
def get_question_bank(
    bank_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    stmt = select(QuestionBank).where(QuestionBank.id == bank_id, QuestionBank.org_id == current_user.org_id)
    bank = db.execute(stmt).scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return bank

@question_bank_router.get("/question-banks/{bank_id}/questions")
def list_questions(
    bank_id: int,
    category_id: Optional[int] = Query(default=None),
    tag_id: Optional[int] = Query(default=None),
    question_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    version_state: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    _validate_bank(db, bank_id, current_user.org_id)
    return _list_questions(
        db,
        current_user.org_id,
        bank_id=bank_id,
        category_id=category_id,
        tag_id=tag_id,
        question_type=question_type,
        search=search,
        status_filter=status,
        version_state=version_state,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

# --- Question Endpoints ---

@question_bank_router.post("/question-banks/{bank_id}/questions")
def create_question(
    bank_id: int,
    req: QuestionCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    _validate_bank(db, bank_id, current_user.org_id)
    _validate_category(db, req.category_id, current_user.org_id)
    _validate_tags(db, req.tag_ids, current_user.org_id)
    svc = QuestionBankService(db)
    q = svc.create_question(
        org_id=current_user.org_id,
        bank_id=bank_id,
        category_id=req.category_id,
        question_type=req.question_type,
        question_text=req.question_text,
        points=req.points,
        options_json=req.options_json,
        correct_answer_json=req.correct_answer_json
    )
    if q.current_draft_version_id:
        _set_version_tags(db, q.current_draft_version_id, current_user.org_id, req.tag_ids)
    db.commit()
    return {"id": q.id, "current_draft_version_id": q.current_draft_version_id, "category_id": q.category_id, "tag_ids": req.tag_ids}

@question_bank_router.put("/question-banks/{bank_id}/questions/{q_id}/draft")
def update_draft_question(
    bank_id: int,
    q_id: int,
    req: QuestionUpdateDraft,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    # Only allows updating if there is an active draft. 
    # If the question is published and has no draft, this fails.
    svc = QuestionBankService(db)
    question = svc.question_repo.get_by_id_and_org(q_id, current_user.org_id)
    if not question or question.bank_id != bank_id:
        raise HTTPException(status_code=404, detail="Question not found")
        
    if not question.current_draft_version_id:
        raise HTTPException(
            status_code=400, 
            detail="No active draft exists. Create a new draft from the published version first."
        )
        
    draft = svc.version_repo.get_by_id_and_org(question.current_draft_version_id, current_user.org_id)
    if not draft or draft.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Invalid draft state")
        
    updates = req.model_dump(exclude_unset=True)
    tag_ids = updates.pop("tag_ids", None)
    category_id = updates.pop("category_id", None)
    if "category_id" in req.model_fields_set:
        _validate_category(db, category_id, current_user.org_id)
        svc.question_repo.update(question, category_id=category_id)
        svc.version_repo.update(draft, category_id=category_id)
    if tag_ids is not None:
        _set_version_tags(db, draft.id, current_user.org_id, tag_ids)
    svc.version_repo.update(draft, **updates)
    db.commit()
    return {"id": q_id, "draft_version_id": draft.id, "status": "updated", "category_id": draft.category_id, "tag_ids": tag_ids}

@question_bank_router.post("/question-banks/{bank_id}/questions/{q_id}/publish")
def publish_question(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_PUBLISH_QUESTIONS)),
    db: Session = Depends(db_session)
):
    svc = QuestionBankService(db)
    try:
        published_version = svc.publish_question(current_user.org_id, q_id)
        db.commit()
        return {"id": q_id, "published_version_id": published_version.id, "status": "published"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@question_bank_router.post("/question-banks/{bank_id}/questions/{q_id}/drafts")
def create_new_draft_from_published(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    """Creates a new DRAFT version based on the current PUBLISHED version."""
    svc = QuestionBankService(db)
    try:
        question = svc.question_repo.get_by_id_and_org(q_id, current_user.org_id)
        if not question or question.bank_id != bank_id:
            raise HTTPException(status_code=404, detail="Question not found")
        published_version_id = question.current_published_version_id
        new_version = svc.edit_published_question(current_user.org_id, q_id, updates={})
        if published_version_id:
            published_tags = _tag_ids_for_versions(db, current_user.org_id, [published_version_id])
            _set_version_tags(
                db,
                new_version.id,
                current_user.org_id,
                published_tags.get(published_version_id, []),
            )
        db.commit()
        return {"id": q_id, "draft_version_id": new_version.id, "status": "draft_created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@question_bank_router.delete("/question-banks/{bank_id}/questions/{q_id}/draft")
def archive_draft_question(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    svc = QuestionBankService(db)
    try:
        svc.archive_draft(current_user.org_id, q_id)
        db.commit()
        return {"status": "archived"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@question_bank_router.get("/question-banks/{bank_id}/questions/{q_id}/versions")
def get_question_versions(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    svc = QuestionBankService(db)
    question = svc.question_repo.get_by_id_and_org(q_id, current_user.org_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    versions = db.execute(
        select(QuestionVersion).where(QuestionVersion.question_id == q_id).order_by(QuestionVersion.created_at.desc())
    ).scalars().all()
    version_tags = _tag_ids_for_versions(db, current_user.org_id, [v.id for v in versions])
    
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
            "is_current_published": v.id == question.current_published_version_id
        }
        for v in versions
    ]

# --- Import Jobs ---

@question_bank_router.post("/question-banks/imports")
def create_import_job(
    req: ImportJobCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    import uuid
    _validate_category(db, req.category_id, current_user.org_id)
    _validate_tags(db, req.tag_ids, current_user.org_id)
    metadata = {
        "file_key": req.file_key,
        "category_id": req.category_id,
        "tag_ids": sorted(set(req.tag_ids)),
    }
    job = QuestionImportJob(
        id=uuid.uuid4().hex,
        org_id=current_user.org_id,
        user_id=current_user.id,
        status="UPLOADED",
        error_log=None,
        metadata_json=metadata,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": job.id, "status": job.status, "metadata_json": job.metadata_json}

class StaleCheckRequest(BaseModel):
    items: List[Dict[str, int]] # [{"question_id": 1, "version_id": 10}]

@question_bank_router.post("/question-banks/check-stale")
def check_stale_versions(
    req: StaleCheckRequest,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session)
):
    result = {}
    for item in req.items:
        q_id = item.get("question_id")
        v_id = item.get("version_id")
        if not q_id or not v_id: continue
        
        q = db.execute(select(Question).where(Question.id == q_id, Question.org_id == current_user.org_id)).scalar_one_or_none()
        if q and q.current_published_version_id and q.current_published_version_id != v_id:
            # We found a newer published version
            result[q_id] = {
                "is_stale": True,
                "latest_version_id": q.current_published_version_id
            }
        else:
            result[q_id] = {
                "is_stale": False,
                "latest_version_id": q.current_published_version_id if q else None
            }
            
    return result
