"""Learner quiz-related endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_admin, TokenData
from app.db.engine import db_session
from app.repositories.progress_repo import ProgressRepository
from app.services.gradebook_service import GradebookService
from app.services.pal_score_service import PALScoreService
from app.models.learner_event import LearnerEvent
from app.models.lesson_block import LessonBlock
from app.models.course_module import CourseModule
from app.models.course import Course
from app.models.user import User
from app.models.lesson_block_progress import LessonBlockProgress
from app.api.routes.learner.schemas import QuizSubmitRequest
from app.api.routes.learner.utils import resolve_block_for_learner

logger = logging.getLogger(__name__)

learner_quiz_router = APIRouter(tags=["Learner Quiz APIs"])


def quiz_attempt_limit(settings: dict) -> int | None:
    """Extract quiz attempt limit from settings."""
    raw = settings.get("max_attempts", settings.get("attempt_limit", 0))
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        value = 0
    return value if value > 0 else None


def quiz_attempt_history(db: Session, *, user_id: str, org_id: int, course_id: str, block_id: int) -> list[dict]:
    """Get quiz attempt history for a user."""
    events = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == user_id,
        LearnerEvent.org_id == org_id,
        LearnerEvent.course_id == course_id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
    ).order_by(LearnerEvent.created_at.asc(), LearnerEvent.id.asc()).all()
    
    history = []
    for index, event in enumerate(events, start=1):
        payload = event.payload_json or {}
        score = float(payload.get("score") or 0)
        history.append({
            "attempt_id": event.id,
            "attempt_number": int(payload.get("attempt_number") or index),
            "attempt_date": event.created_at.isoformat() if event.created_at else None,
            "score": score,
            "status": "passed" if payload.get("passed") else "failed",
            "passed": bool(payload.get("passed")),
            "correct": payload.get("correct"),
            "total": payload.get("total"),
            "points_awarded": payload.get("points_awarded"),
            "points_total": payload.get("points_total"),
        })
    return history


def quiz_stats_payload(settings: dict, history: list[dict]) -> dict:
    """Generate quiz statistics payload."""
    max_attempts = quiz_attempt_limit(settings)
    attempts_used = len(history)
    attempts_remaining = None if max_attempts is None else max(max_attempts - attempts_used, 0)
    highest_score = max((attempt["score"] for attempt in history), default=0.0)
    latest_score = history[-1]["score"] if history else None
    best_attempt = max(history, key=lambda item: item["score"], default=None)
    average_score = sum(attempt["score"] for attempt in history) / attempts_used if attempts_used else 0.0
    completion_status = "completed" if any(attempt["passed"] for attempt in history) else "attempted" if history else "not_started"
    return {
        "maximum_attempts": max_attempts,
        "max_attempts": max_attempts,
        "attempts_used": attempts_used,
        "attempts_remaining": attempts_remaining,
        "highest_score": round(highest_score, 2),
        "latest_score": round(latest_score, 2) if latest_score is not None else None,
        "best_attempt": best_attempt,
        "average_score": round(average_score, 2),
        "completion_status": completion_status,
        "attempt_history": history,
    }


@learner_quiz_router.get("/blocks/{block_id}/quiz/stats")
async def get_quiz_stats(
    block_id: int,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Get quiz statistics for a learner."""
    block, course_id = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") not in ("quiz", "native_quiz"):
        raise HTTPException(status_code=400, detail="Block is not a quiz")
    settings = block.get("metadata_json", {})
    history = quiz_attempt_history(db, user_id=current_user.id, org_id=current_user.org_id, course_id=course_id, block_id=block_id)
    return quiz_stats_payload(settings, history)


@learner_quiz_router.get("/admin/categories/{category_slug}/quiz-statistics")
def get_category_quiz_statistics(
    category_slug: str,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(require_admin),
):
    """Get quiz statistics for all learners in a category (admin only)."""
    if current_user.role == "category_admin" and current_user.category_scope != category_slug:
        raise HTTPException(status_code=403, detail="You do not have access to this category.")

    learners = db.query(User).filter(
        User.role == "learner",
        User.category_scope == category_slug,
        User.org_id == current_user.org_id,
    ).order_by(User.full_name.asc()).all()
    
    quiz_blocks = db.query(LessonBlock, CourseModule, Course).join(
        CourseModule, LessonBlock.module_id == CourseModule.id
    ).join(
        Course, CourseModule.course_id == Course.id
    ).filter(
        LessonBlock.org_id == current_user.org_id,
        Course.org_id == current_user.org_id,
        Course.category_slug == category_slug,
        LessonBlock.block_type.in_(("quiz", "native_quiz")),
        LessonBlock.deleted_at.is_(None),
        CourseModule.deleted_at.is_(None),
    ).all()

    # Collect all learner IDs, block IDs, and course IDs for batch query.
    # Keep the block/course tuples only for the response builder below; the SQL
    # filter itself must use scalar columns so PostgreSQL can compare them
    # correctly instead of treating a tuple as a single `block_id` value.
    learner_ids = [learner.id for learner in learners]
    block_ids = [block.id for block, _, _ in quiz_blocks]
    block_info = {(block.id, course.id): (block, module, course) for block, module, course in quiz_blocks}
    course_ids = {course.id for _, _, course in quiz_blocks}

    # Batch fetch all LearnerEvent records for all (learner, block, course)
    # combinations while keeping the original safety filters.
    all_events = db.query(LearnerEvent).filter(
        LearnerEvent.user_id.in_(learner_ids),
        LearnerEvent.org_id == current_user.org_id,
        LearnerEvent.course_id.in_(course_ids),
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
        LearnerEvent.block_id.in_(block_ids),
    ).order_by(LearnerEvent.created_at.asc(), LearnerEvent.id.asc()).all()
    
    # Group events by (user_id, block_id, course_id) to preserve course boundaries
    events_by_user_block_course = {}
    for event in all_events:
        key = (event.user_id, event.block_id, event.course_id)
        if key not in events_by_user_block_course:
            events_by_user_block_course[key] = []
        events_by_user_block_course[key].append(event)
    
    rows = []
    for learner in learners:
        learner_attempts = []
        for (block_id, course_id), (block, module, course) in block_info.items():
            # Retrieve events for specific (user_id, block_id, course_id) combination
            # This is equivalent to quiz_attempt_history() with specific course_id
            events = events_by_user_block_course.get((learner.id, block_id, course_id), [])
            history = []
            for index, event in enumerate(events, start=1):
                payload = event.payload_json or {}
                score = float(payload.get("score") or 0)
                history.append({
                    "attempt_id": event.id,
                    "attempt_number": int(payload.get("attempt_number") or index),
                    "attempt_date": event.created_at.isoformat() if event.created_at else None,
                    "score": score,
                    "status": "passed" if payload.get("passed") else "failed",
                    "passed": bool(payload.get("passed")),
                    "correct": payload.get("correct"),
                    "total": payload.get("total"),
                    "points_awarded": payload.get("points_awarded"),
                    "points_total": payload.get("points_total"),
                })
            settings = block.metadata_json or {}
            stats = quiz_stats_payload(settings, history)
            learner_attempts.append({
                "course_id": course.id,
                "course_name": course.name,
                "module_id": module.id,
                "module_title": module.title,
                "block_id": block.id,
                "quiz_title": block.content or settings.get("title") or "Quiz",
                **stats,
            })
        scores = [item["highest_score"] for item in learner_attempts if item["attempts_used"] > 0]
        rows.append({
            "learner": {
                "id": learner.id,
                "full_name": learner.full_name,
                "email": learner.email,
            },
            "attempts_used": sum(item["attempts_used"] for item in learner_attempts),
            "attempts_remaining": None if any(item["attempts_remaining"] is None for item in learner_attempts) else sum(item["attempts_remaining"] for item in learner_attempts),
            "highest_score": round(max(scores), 2) if scores else 0.0,
            "latest_score": next((item["latest_score"] for item in reversed(learner_attempts) if item["latest_score"] is not None), None),
            "best_attempt": max((item["best_attempt"] for item in learner_attempts if item["best_attempt"]), key=lambda item: item["score"], default=None),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "completion_status": "completed" if any(item["completion_status"] == "completed" for item in learner_attempts) else "attempted" if scores else "not_started",
            "quizzes": learner_attempts,
        })

    return {"rows": rows}


@learner_quiz_router.post("/blocks/{block_id}/quiz/submit")
async def submit_quiz(
    block_id: int,
    request: QuizSubmitRequest,
    db: Session = Depends(db_session),
    current_user: TokenData = Depends(get_current_user)
):
    """Submit a quiz attempt."""
    block, course_id = resolve_block_for_learner(block_id, db, current_user.id, current_user.org_id)
    if block.get("block_type") not in ("quiz", "native_quiz"):
        raise HTTPException(status_code=400, detail="Block is not a quiz")
    
    settings = block.get("metadata_json", {})
    questions = settings.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="Quiz has no questions")

    max_attempts = quiz_attempt_limit(settings)
    prior_attempts = db.query(LearnerEvent).filter(
        LearnerEvent.user_id == current_user.id,
        LearnerEvent.org_id == current_user.org_id,
        LearnerEvent.course_id == course_id,
        LearnerEvent.block_id == block_id,
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
    ).count()
    if max_attempts is not None and prior_attempts >= max_attempts:
        raise HTTPException(status_code=403, detail="You have reached the maximum number of allowed attempts.")

    correct = 0
    total = len(questions)
    total_points = 0
    awarded_points = 0
    question_results = []
    for q in questions:
        q_id = str(q.get("id"))
        correct_option_id = q.get("correct_option_id")
        if not correct_option_id:
            raise HTTPException(status_code=400, detail="Quiz question is missing a correct option")
        points = int(q.get("points") or 1)
        total_points += points
        selected_option_id = request.answers.get(q_id)
        is_correct = selected_option_id == correct_option_id
        if is_correct:
            correct += 1
            awarded_points += points
        question_results.append({
            "question_id": q_id,
            "is_correct": is_correct,
            "points": points,
            "points_awarded": points if is_correct else 0,
        })
            
    score = (awarded_points / total_points) * 100 if total_points > 0 else 0
    passed = score >= int(settings.get("passing_score") or 80)

    progress_repo = ProgressRepository(db)
    bp = progress_repo.get_block_progress(current_user.id, block_id, current_user.org_id)
    if not bp:
        bp = LessonBlockProgress(
            user_id=current_user.id,
            block_id=block_id,
            module_id=block.get("module_id"),
            org_id=current_user.org_id,
            status="completed" if passed else "in_progress",
            completed_at=datetime.utcnow() if passed else None
        )
        db.add(bp)
    else:
        if passed:
            bp.status = "completed"
            bp.completed_at = datetime.utcnow()
            
    quiz_event = LearnerEvent(
        user_id=current_user.id,
        course_id=course_id,
        module_id=block.get("module_id"),
        block_id=block_id,
        event_type="QUIZ_SUBMITTED",
        schema_version="1.0",
        payload_json={
            "score": score,
            "passed": passed,
            "correct": correct,
            "total": total,
            "points_awarded": awarded_points,
            "points_total": total_points,
            "attempt_number": prior_attempts + 1,
            "max_attempts": max_attempts,
        },
        created_at=datetime.utcnow(),
        org_id=current_user.org_id
    )
    db.add(quiz_event)
    db.flush()

    gradebook = GradebookService(db)
    grade_item = gradebook.ensure_quiz_grade_item(
        org_id=current_user.org_id,
        course_id=course_id,
        block_id=block_id,
        title=block.get("content") or settings.get("title") or "Quiz",
        settings=settings,
        actor_user_id=current_user.id,
    )
    gradebook.upsert_current_result(
        org_id=current_user.org_id,
        course_id=course_id,
        course_version_id=gradebook.course_version_token(
            user_id=current_user.id,
            course_id=course_id,
            org_id=current_user.org_id,
        ),
        grade_item=grade_item,
        user_id=current_user.id,
        source_type="quiz_submission",
        source_id=str(quiz_event.id),
        attempt_number=prior_attempts + 1,
        points_awarded=float(awarded_points),
        points_possible=float(total_points),
        percentage=float(score),
        status="graded",
        graded_by=None,
        graded_at=quiz_event.created_at,
        feedback=None,
        metadata={
            "passed": passed,
            "correct": correct,
            "total": total,
            "attempt_number": prior_attempts + 1,
            "max_attempts": max_attempts,
            "attempt_strategy": (grade_item.grading_policy_json or {}).get("attempt_strategy", "best"),
            "question_results": question_results,
            "source_event_id": quiz_event.id,
        },
    )
    PALScoreService(db).recompute_user(current_user.id, current_user.org_id)
    db.commit()
    history = quiz_attempt_history(db, user_id=current_user.id, org_id=current_user.org_id, course_id=course_id, block_id=block_id)
    stats = quiz_stats_payload(settings, history)
    
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "passed": passed,
        "attempt_number": prior_attempts + 1,
        "max_attempts": max_attempts,
        "attempts_remaining": stats["attempts_remaining"],
        "attempts_used": stats["attempts_used"],
        "highest_score": stats["highest_score"],
        "latest_score": stats["latest_score"],
        "best_attempt": stats["best_attempt"],
        "attempt_history": stats["attempt_history"],
        "question_results": question_results,
    }
