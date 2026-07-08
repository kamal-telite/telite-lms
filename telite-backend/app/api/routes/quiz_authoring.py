from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.models.question_bank import QuestionBank
from app.models.question import Question, QuestionVersion
from app.models.quiz_models import QuizDefinition, QuizSettings
from app.models.rubric import GradingRubric, RubricCriteria

quiz_authoring_router = APIRouter(
    prefix="/quiz-authoring",
    tags=["Quiz Authoring"],
)

class QuestionBankCreate(BaseModel):
    name: str
    visibility: str = "tenant"

@quiz_authoring_router.post("/banks", dependencies=[Depends(require_admin)])
def create_question_bank(
    request: QuestionBankCreate,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    bank = QuestionBank(
        org_id=current_user.org_id,
        name=request.name,
        visibility=request.visibility
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank.to_dict() if hasattr(bank, "to_dict") else {"id": bank.id, "name": bank.name, "visibility": bank.visibility}

class QuestionCreate(BaseModel):
    bank_id: int
    question_type: str
    question_text: str
    options_json: Optional[dict] = None
    correct_answer_json: Optional[dict] = None
    points: int = 1
    metadata_json: Optional[dict] = None

@quiz_authoring_router.post("/banks/{bank_id}/questions", dependencies=[Depends(require_admin)])
def create_question(
    bank_id: int,
    request: QuestionCreate,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    bank = db.query(QuestionBank).filter(QuestionBank.id == bank_id, QuestionBank.org_id == current_user.org_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
        
    question = Question(bank_id=bank.id, org_id=current_user.org_id)
    db.add(question)
    db.flush()
    
    version = QuestionVersion(
        question_id=question.id,
        org_id=current_user.org_id,
        version_number=1,
        question_type=request.question_type,
        question_text=request.question_text,
        options_json=request.options_json,
        correct_answer_json=request.correct_answer_json,
        points=request.points,
        metadata_json=request.metadata_json
    )
    db.add(version)
    db.flush()
    
    question.current_version_id = version.id
    db.commit()
    db.refresh(question)
    return {"question_id": question.id, "version_id": version.id}

class QuizSettingsUpdate(BaseModel):
    passing_score: Optional[int] = None
    time_limit: Optional[int] = None
    attempt_limit: Optional[int] = None
    review_mode: Optional[str] = None
    show_answers: Optional[bool] = None
    show_score: Optional[bool] = None

@quiz_authoring_router.put("/quizzes/{quiz_id}/settings", dependencies=[Depends(require_admin)])
def update_quiz_settings(
    quiz_id: int,
    request: QuizSettingsUpdate,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    quiz = db.query(QuizDefinition).filter(
        QuizDefinition.id == quiz_id,
        QuizDefinition.org_id == current_user.org_id,
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    payload = request.model_dump(exclude_unset=True)

    if request.passing_score is not None:
        quiz.passing_score = request.passing_score
    if request.time_limit is not None:
        quiz.time_limit = request.time_limit
    if request.attempt_limit is not None:
        quiz.attempt_limit = request.attempt_limit
    if request.review_mode is not None:
        quiz.review_mode = request.review_mode

    quiz.settings_json = payload

    settings_row = db.query(QuizSettings).filter(
        QuizSettings.quiz_id == quiz.id,
        QuizSettings.org_id == current_user.org_id,
    ).first()
    if settings_row is None:
        settings_row = QuizSettings(quiz_id=quiz.id, org_id=current_user.org_id)
        db.add(settings_row)

    for field_name in ["passing_score", "time_limit", "attempt_limit", "review_mode", "show_answers", "show_score"]:
        if field_name in payload:
            setattr(settings_row, field_name, payload[field_name])

    settings_row.settings_json = payload
    db.add(settings_row)
    db.commit()
    db.refresh(settings_row)
    return {
        "id": quiz.id,
        "title": quiz.title,
        "passing_score": quiz.passing_score,
        "time_limit": quiz.time_limit,
        "attempt_limit": quiz.attempt_limit,
        "review_mode": quiz.review_mode,
    }

class RubricCreate(BaseModel):
    name: str

@quiz_authoring_router.post("/rubrics", dependencies=[Depends(require_admin)])
def create_rubric(
    request: RubricCreate,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    rubric = GradingRubric(org_id=current_user.org_id, name=request.name)
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return {"id": rubric.id, "name": rubric.name}
