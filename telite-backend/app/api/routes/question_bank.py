from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import TokenData
from app.core.rbac import Permission, require_permission
from app.db.engine import db_session
from app.models.question_bank import QuestionBank

from app.features.question_bank.crud import (
    archive_draft_question,
    check_stale_versions as crud_check_stale_versions,
    create_category,
    create_import_job,
    create_new_draft_from_published,
    create_question,
    create_tag,
    delete_category,
    delete_tag,
    get_question_versions,
    list_categories,
    list_questions as crud_list_questions,
    list_tags,
    publish_question as crud_publish_question,
    update_category,
    update_draft_question,
    update_tag,
)
from app.features.question_bank.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ImportJobCreate,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionCreate,
    QuestionUpdateDraft,
    StaleCheckRequest,
    TagCreate,
    TagUpdate,
)
from app.features.question_bank.validation import validate_bank

question_bank_router = APIRouter(tags=["Question Bank"])


@question_bank_router.post("/question-banks", response_model=QuestionBankResponse)
def create_question_bank(
    req: QuestionBankCreate,
    current_user: TokenData = Depends(require_permission(Permission.ORG_MANAGE_BANKS)),
    db: Session = Depends(db_session),
):
    bank = QuestionBank(org_id=current_user.org_id, name=req.name)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@question_bank_router.get("/question-banks", response_model=List[QuestionBankResponse])
def list_question_banks(
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
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
    db: Session = Depends(db_session),
):
    if bank_id is not None:
        validate_bank(db, bank_id, current_user.org_id)
    return crud_list_questions(
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
    db: Session = Depends(db_session),
):
    return list_categories(db, current_user.org_id, tree)


@question_bank_router.post("/question-banks/categories")
def create_category_route(
    req: CategoryCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return create_category(db, current_user.org_id, req)


@question_bank_router.put("/question-banks/categories/{category_id}")
def update_category_route(
    category_id: int,
    req: CategoryUpdate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return update_category(db, current_user.org_id, category_id, req)


@question_bank_router.delete("/question-banks/categories/{category_id}")
def delete_category_route(
    category_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return delete_category(db, current_user.org_id, category_id)


@question_bank_router.get("/question-banks/tags")
def list_tags_route(
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return list_tags(db, current_user.org_id)


@question_bank_router.post("/question-banks/tags")
def create_tag_route(
    req: TagCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return create_tag(db, current_user.org_id, req)


@question_bank_router.put("/question-banks/tags/{tag_id}")
def update_tag_route(
    tag_id: int,
    req: TagUpdate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return update_tag(db, current_user.org_id, tag_id, req)


@question_bank_router.delete("/question-banks/tags/{tag_id}")
def delete_tag_route(
    tag_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return delete_tag(db, current_user.org_id, tag_id)


@question_bank_router.get("/question-banks/{bank_id}", response_model=QuestionBankResponse)
def get_question_bank(
    bank_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
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
    db: Session = Depends(db_session),
):
    validate_bank(db, bank_id, current_user.org_id)
    return crud_list_questions(
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


@question_bank_router.post("/question-banks/{bank_id}/questions")
def create_question_route(
    bank_id: int,
    req: QuestionCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    validate_bank(db, bank_id, current_user.org_id)
    return create_question(db, current_user.org_id, bank_id, req)


@question_bank_router.put("/question-banks/{bank_id}/questions/{q_id}/draft")
def update_draft_question_route(
    bank_id: int,
    q_id: int,
    req: QuestionUpdateDraft,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return update_draft_question(db, current_user.org_id, bank_id, q_id, req)


@question_bank_router.post("/question-banks/{bank_id}/questions/{q_id}/publish")
def publish_question_route(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_PUBLISH_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return crud_publish_question(db, current_user.org_id, q_id)


@question_bank_router.post("/question-banks/{bank_id}/questions/{q_id}/drafts")
def create_new_draft_from_published_route(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return create_new_draft_from_published(db, current_user.org_id, bank_id, q_id)


@question_bank_router.delete("/question-banks/{bank_id}/questions/{q_id}/draft")
def archive_draft_question_route(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return archive_draft_question(db, current_user.org_id, q_id)


@question_bank_router.get("/question-banks/{bank_id}/questions/{q_id}/versions")
def get_question_versions_route(
    bank_id: int,
    q_id: int,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return get_question_versions(db, current_user.org_id, bank_id, q_id)


@question_bank_router.post("/question-banks/imports")
def create_import_job_route(
    req: ImportJobCreate,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return create_import_job(db, current_user.org_id, current_user.id, req)


@question_bank_router.post("/question-banks/check-stale")
def check_stale_versions_route(
    req: StaleCheckRequest,
    current_user: TokenData = Depends(require_permission(Permission.AUTHORING_MANAGE_QUESTIONS)),
    db: Session = Depends(db_session),
):
    return crud_check_stale_versions(db, current_user.org_id, req)
