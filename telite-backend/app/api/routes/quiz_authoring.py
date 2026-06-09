from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.models.question_bank import QuestionBank
from app.models.question import Question, QuestionVersion
from app.models.quiz_models import QuizSettings, QuizDefinition
from app.models.rubric import GradingRubric, RubricCriteria

quiz_authoring_router = APIRouter(prefix="/quiz-authoring", tags=["Quiz Authoring"])

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
    return {"question_id": question.id, "version_id": version.id}

class QuizSettingsUpdate(BaseModel):
    time_limit: Optional[int] = None
    passing_score: Optional[float] = None
    attempt_limit: Optional[int] = None
    show_answers: bool = False
    show_score: bool = True
    shuffle_questions: bool = False
    shuffle_options: bool = False
    cooldown_minutes: Optional[int] = None
    review_mode: str = "score_only"

@quiz_authoring_router.put("/quizzes/{quiz_id}/settings", dependencies=[Depends(require_admin)])
def update_quiz_settings(
    quiz_id: int,
    request: QuizSettingsUpdate,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    quiz = db.query(QuizDefinition).filter(QuizDefinition.id == quiz_id, QuizDefinition.org_id == current_user.org_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    settings = db.query(QuizSettings).filter(QuizSettings.quiz_id == quiz_id).first()
    if not settings:
        settings = QuizSettings(quiz_id=quiz_id)
        db.add(settings)
        
    for key, value in request.dict(exclude_unset=True).items():
        setattr(settings, key, value)
        
    db.commit()
    return {"success": True}

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
