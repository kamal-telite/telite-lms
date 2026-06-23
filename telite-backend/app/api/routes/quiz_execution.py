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
from app.models.course import Course
from app.services.gradebook_service import GradebookService

quiz_execution_router = APIRouter(
    prefix="/quiz-execution",
    tags=["Quiz Execution"],
)

@quiz_execution_router.post("/blocks/{block_id}/attempts")
def start_attempt(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    block = db.query(LessonBlock).filter(LessonBlock.id == block_id, LessonBlock.org_id == current_user.org_id).first()
    if not block or block.block_type != "quiz":
        raise HTTPException(status_code=404, detail="Quiz block not found")
        
    settings = block.metadata_json or {}
    questions = settings.get("questions", [])
    
    # Check attempt limits
    attempt_limit = settings.get("attempt_limit")
    if attempt_limit is not None:
        past_attempts = db.query(QuizAttempt).filter(
            QuizAttempt.lesson_block_id == block_id,
            QuizAttempt.user_id == current_user.id
        ).count()
        if past_attempts >= attempt_limit:
            raise HTTPException(status_code=403, detail="Attempt limit reached")
    
    attempt = QuizAttempt(
        lesson_block_id=block_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        status="in_progress",
        started_at=datetime.now(timezone.utc)
    )
    db.add(attempt)
    db.flush()
    
    # Instantiate attempt questions to freeze the version
    for i, q in enumerate(questions):
        aq = QuizAttemptQuestion(
            attempt_id=attempt.id,
            question_version_id=q.get("question_version_id"),
            display_order=i,
            org_id=current_user.org_id
        )
        db.add(aq)
    
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

    block = db.query(LessonBlock).filter(LessonBlock.id == attempt.lesson_block_id).first()
    settings = block.metadata_json or {}

    # Server-side time limit enforcement
    time_limit = settings.get("time_limit_minutes")
    if time_limit and attempt.started_at:
        from datetime import timedelta
        deadline = attempt.started_at + timedelta(minutes=time_limit)
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
    
    answers = db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt.id).all()
    total_score = 0
    all_auto_graded = True
    
    # We need a map of question_version_id to points
    points_map = {q["question_version_id"]: q.get("points", 1) for q in settings.get("questions", [])}

    for answer in answers:
        question_version = db.query(QuestionVersion).filter(QuestionVersion.id == answer.question_version_id).first()
        if question_version and question_version.question_type in ["multiple_choice", "true_false"]:
            correct_ans = question_version.correct_answer_json.get("answer") if question_version.correct_answer_json else None
            student_ans = answer.response_json.get("answer") if answer.response_json else None
            
            pts_available = points_map.get(answer.question_version_id, 1)
            
            if correct_ans and student_ans == correct_ans:
                answer.is_correct = True
                answer.points_awarded = float(pts_available)
                total_score += pts_available
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
        
        # Trigger Gradebook
        # We need course_id. Module -> Course mapping
        from app.models.course_module import CourseModule
        module = db.query(CourseModule).filter(CourseModule.id == block.module_id).first()
        if module:
            gradebook = GradebookService(db)
            grade_item = gradebook.ensure_quiz_grade_item(
                org_id=current_user.org_id, course_id=module.course_id, block_id=block.id,
                title=block.metadata_json.get("title", "Quiz"), settings=settings, actor_user_id=current_user.id
            )
            # Find course version id
            from app.services.gradebook_service import GradebookService
            version_id = gradebook.course_version_token(user_id=current_user.id, course_id=module.course_id, org_id=current_user.org_id)
            
            gradebook.upsert_current_result(
                org_id=current_user.org_id,
                course_id=module.course_id,
                course_version_id=version_id,
                grade_item=grade_item,
                user_id=current_user.id,
                source_type="quiz_block",
                source_id=str(block.id),
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
