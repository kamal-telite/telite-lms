from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api.auth import get_current_user, TokenData
from app.db.engine import db_session
from app.models.lesson_block import LessonBlock
from app.models.quiz_attempt import QuizAttempt, QuizAttemptEvent, QuizAttemptQuestion
from app.models.quiz_answer import QuizAnswer, GradingEvent
from app.models.question import QuestionVersion
from app.models.quiz_models import QuizDefinition
from app.models.course import Course
from app.services.gradebook_service import GradebookService

quiz_execution_router = APIRouter(
    prefix="/quiz-execution",
    tags=["Quiz Execution"],
)

@quiz_execution_router.post("/quizzes/{quiz_id}/attempts")
def start_attempt(
    quiz_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    quiz = db.query(QuizDefinition).filter(
        QuizDefinition.id == quiz_id,
        QuizDefinition.org_id == current_user.org_id,
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    settings = dict(quiz.settings_json or {})
    settings.setdefault("passing_score", quiz.passing_score)
    settings.setdefault("time_limit", quiz.time_limit)
    settings.setdefault("attempt_limit", quiz.attempt_limit)
    settings.setdefault("review_mode", quiz.review_mode)

    attempt = QuizAttempt(
        quiz_definition_id=quiz.id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
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
        answer = QuizAnswer(attempt_id=attempt_id, question_version_id=request.question_version_id, org_id=current_user.org_id)
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

    quiz = None
    settings = {}
    if attempt.quiz_definition_id:
        quiz = db.query(QuizDefinition).filter(QuizDefinition.id == attempt.quiz_definition_id).first()
    if quiz is not None:
        settings = dict(quiz.settings_json or {})
        settings.setdefault("passing_score", quiz.passing_score)
        settings.setdefault("time_limit", quiz.time_limit)
        settings.setdefault("attempt_limit", quiz.attempt_limit)
        settings.setdefault("review_mode", quiz.review_mode)

    # Server-side time limit enforcement
    time_limit = settings.get("time_limit") or settings.get("time_limit_minutes")
    if time_limit and attempt.started_at:
        from datetime import timedelta
        started_at = attempt.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        deadline = started_at + timedelta(minutes=time_limit)
        if datetime.now(timezone.utc) > deadline:
            attempt.status = "timed_out"
            attempt.submitted_at = datetime.now(timezone.utc)
            db.add(QuizAttemptEvent(
                attempt_id=attempt.id, org_id=current_user.org_id,
                event_type="QUIZ_TIMED_OUT", metadata_json={"time_limit_minutes": time_limit}
            ))
            db.commit()
            raise HTTPException(status_code=400, detail="Quiz time limit expired")
        
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    db.add(QuizAttemptEvent(attempt_id=attempt.id, org_id=current_user.org_id, event_type="QUIZ_SUBMITTED"))
    db.add(QuizAttemptEvent(attempt_id=attempt.id, org_id=current_user.org_id, event_type="MANUAL_SUBMIT"))
    
    answers = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).all()
    total_score = 0
    all_auto_graded = True

    points_map = {}
    for question in settings.get("questions", []):
        if isinstance(question, dict) and question.get("question_version_id") is not None:
            points_map[question["question_version_id"]] = question.get("points", 1)

    for answer in answers:
        question_version = db.query(QuestionVersion).filter(QuestionVersion.id == answer.question_version_id).first()
        if question_version and question_version.question_type in ["multiple_choice", "true_false"]:
            correct_ans = question_version.correct_answer_json.get("answer") if question_version.correct_answer_json else None
            student_ans = answer.response_json.get("answer") if answer.response_json else None

            pts_available = points_map.get(answer.question_version_id, question_version.points or 1)

            if correct_ans is not None and student_ans is not None and str(student_ans).lower() == str(correct_ans).lower():
                answer.is_correct = True
                answer.points_awarded = float(pts_available)
                total_score += float(pts_available)
            else:
                answer.is_correct = False
                answer.points_awarded = 0.0

            db.add(GradingEvent(
                attempt_id=attempt.id, org_id=current_user.org_id, grader_id="system",
                new_score=answer.points_awarded, action="AUTO_GRADE_APPLIED"
            ))
        else:
            all_auto_graded = False
            
    attempt.total_score = float(total_score)
    passing_score = settings.get("passing_score")
    if passing_score is not None:
        attempt.passed = total_score >= passing_score
        
    if all_auto_graded:
        attempt.status = "graded"
        db.add(QuizAttemptEvent(attempt_id=attempt.id, org_id=current_user.org_id, event_type="GRADING_COMPLETED"))
        
        if quiz is not None and quiz.module_id is not None:
            from app.models.course_module import CourseModule
            module = db.query(CourseModule).filter(CourseModule.id == quiz.module_id).first()
            if module:
                gradebook = GradebookService(db)
                grade_item = gradebook.ensure_quiz_grade_item(
                    org_id=current_user.org_id, course_id=module.course_id, block_id=quiz.id,
                    title=quiz.title or "Quiz", settings=settings, actor_user_id=current_user.id
                )
                version_id = gradebook.course_version_token(user_id=current_user.id, course_id=module.course_id, org_id=current_user.org_id)

                gradebook.upsert_current_result(
                    org_id=current_user.org_id,
                    course_id=module.course_id,
                    course_version_id=version_id,
                    grade_item=grade_item,
                    user_id=current_user.id,
                    source_type="quiz_block",
                    source_id=str(quiz.id),
                    attempt_number=None,
                    points_awarded=total_score,
                    points_possible=gradebook.quiz_points_possible(settings),
                    percentage=total_score / gradebook.quiz_points_possible(settings) if gradebook.quiz_points_possible(settings) > 0 else 0,
                    status="graded",
                    graded_by="system",
                    graded_at=datetime.now(timezone.utc),
                    feedback=None,
                    metadata={"attempt_id": attempt.id}
                )

    else:
        attempt.status = "needs_manual_grading"
        
    db.commit()
    return {"success": True, "status": attempt.status, "total_score": attempt.total_score}
