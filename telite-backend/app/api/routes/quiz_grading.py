from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.models.quiz_attempt import QuizAttempt, QuizAttemptEvent
from app.models.quiz_answer import QuizAnswer, GradingEvent

quiz_grading_router = APIRouter(prefix="/quiz-grading", tags=["Quiz Grading"])

@quiz_grading_router.get("/pending", dependencies=[Depends(require_admin)])
def list_pending_grading(
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.org_id == current_user.org_id,
        QuizAttempt.status == "needs_manual_grading"
    ).all()
    
    return {"pending_attempts": [{"id": a.id, "quiz_id": a.quiz_id, "user_id": a.user_id} for a in attempts]}

class ManualGradeRequest(BaseModel):
    new_score: float
    feedback: str = ""

@quiz_grading_router.put("/attempts/{attempt_id}/answers/{ans_id}", dependencies=[Depends(require_admin)])
def apply_manual_grade(
    attempt_id: int,
    ans_id: int,
    request: ManualGradeRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    answer = db.query(QuizAnswer).filter(QuizAnswer.id == ans_id, QuizAnswer.attempt_id == attempt_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
        
    previous_score = answer.points_awarded
    answer.points_awarded = request.new_score
    answer.instructor_feedback = request.feedback
    
    event = GradingEvent(
        attempt_id=attempt_id,
        org_id=current_user.org_id,
        grader_id=current_user.id,
        previous_score=previous_score,
        new_score=request.new_score,
        action="MANUAL_GRADE_APPLIED"
    )
    db.add(event)
    
    # Check if attempt is fully graded
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    attempt.status = "graded"
    
    completion_event = QuizAttemptEvent(
        attempt_id=attempt.id,
        org_id=current_user.org_id,
        event_type="GRADING_COMPLETED"
    )
    db.add(completion_event)
    
    db.commit()
    return {"success": True}
