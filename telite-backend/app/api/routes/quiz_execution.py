from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.quiz_models import QuizDefinition, QuizSettings
from app.models.quiz_attempt import QuizAttempt, QuizAttemptEvent
from app.models.quiz_answer import QuizAnswer, GradingEvent
from app.models.question import QuestionVersion

quiz_execution_router = APIRouter(prefix="/quiz-execution", tags=["Quiz Execution"])

@quiz_execution_router.post("/quizzes/{quiz_id}/attempts")
def start_attempt(
    quiz_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    quiz = db.query(QuizDefinition).filter(QuizDefinition.id == quiz_id, QuizDefinition.org_id == current_user.org_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    # Check attempt limits, active attempts etc. (mocked logic)
    
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        status="in_progress",
        started_at=datetime.now(timezone.utc)
    )
    db.add(attempt)
    db.flush()
    
    event = QuizAttemptEvent(
        attempt_id=attempt.id,
        org_id=current_user.org_id,
        event_type="QUIZ_STARTED",
        metadata_json={"ip_address": "127.0.0.1", "user_agent": "Mock/1.0"}
    )
    db.add(event)
    db.commit()
    return {"attempt_id": attempt.id, "status": attempt.status}

class SaveAnswerRequest(BaseModel):
    question_version_id: int
    response_json: dict

@quiz_execution_router.put("/attempts/{attempt_id}/answers")
def save_answer(
    attempt_id: int,
    request: SaveAnswerRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == current_user.id).first()
    if not attempt or attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Invalid attempt")
        
    answer = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt_id, QuizAnswer.question_version_id == request.question_version_id).first()
    if not answer:
        answer = QuizAnswer(attempt_id=attempt_id, question_version_id=request.question_version_id)
        db.add(answer)
        
    answer.response_json = request.response_json
    
    event = QuizAttemptEvent(
        attempt_id=attempt.id,
        org_id=current_user.org_id,
        event_type="ANSWER_SAVED",
        metadata_json={"question_version_id": request.question_version_id}
    )
    db.add(event)
    
    db.commit()
    return {"success": True}

@quiz_execution_router.post("/attempts/{attempt_id}/submit")
def submit_attempt(
    attempt_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == current_user.id).first()
    if not attempt or attempt.status != "in_progress":
        raise HTTPException(status_code=400, detail="Invalid attempt")

    # ── Server-side time limit enforcement ───────────────────────────────
    settings = db.query(QuizSettings).filter(QuizSettings.quiz_id == attempt.quiz_id).first()
    if settings and settings.time_limit and attempt.started_at:
        from datetime import timedelta
        deadline = attempt.started_at + timedelta(minutes=settings.time_limit)
        if datetime.now(timezone.utc) > deadline:
            # Auto-submit as timed out — grade what's been answered
            attempt.status = "timed_out"
            attempt.submitted_at = datetime.now(timezone.utc)
            timeout_event = QuizAttemptEvent(
                attempt_id=attempt.id,
                org_id=current_user.org_id,
                event_type="QUIZ_TIMED_OUT",
                metadata_json={"time_limit_minutes": settings.time_limit},
            )
            db.add(timeout_event)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Quiz time limit of {settings.time_limit} minutes has expired. Your attempt has been auto-submitted.",
            )
        
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    
    event = QuizAttemptEvent(
        attempt_id=attempt.id,
        org_id=current_user.org_id,
        event_type="QUIZ_SUBMITTED"
    )
    db.add(event)
    
    # Auto-grading trigger
    answers = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).all()
    total_score = 0
    all_auto_graded = True
    
    for answer in answers:
        question_version = db.query(QuestionVersion).filter(QuestionVersion.id == answer.question_version_id).first()
        if question_version.question_type in ["multiple_choice", "true_false"]:
            # Mock grading logic
            correct_ans = question_version.correct_answer_json.get("answer") if question_version.correct_answer_json else None
            student_ans = answer.response_json.get("answer") if answer.response_json else None
            
            if correct_ans and student_ans == correct_ans:
                answer.is_correct = 1
                answer.points_awarded = float(question_version.points)
                total_score += question_version.points
            else:
                answer.is_correct = 0
                answer.points_awarded = 0.0
                
            grade_event = GradingEvent(
                attempt_id=attempt.id,
                org_id=current_user.org_id,
                grader_id="system",
                previous_score=None,
                new_score=answer.points_awarded,
                action="AUTO_GRADE_APPLIED"
            )
            db.add(grade_event)
        else:
            all_auto_graded = False
            
    attempt.total_score = float(total_score)
    if settings and settings.passing_score is not None:
        attempt.passed = 1 if total_score >= settings.passing_score else 0
        
    if all_auto_graded:
        attempt.status = "graded"
        completion_event = QuizAttemptEvent(
            attempt_id=attempt.id,
            org_id=current_user.org_id,
            event_type="GRADING_COMPLETED"
        )
        db.add(completion_event)
    else:
        attempt.status = "needs_manual_grading"
        
    db.commit()
    return {"success": True, "status": attempt.status, "total_score": attempt.total_score}
