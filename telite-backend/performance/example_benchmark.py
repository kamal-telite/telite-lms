"""
Example: Benchmarking the Quiz Statistics Endpoint

This script demonstrates how to use the performance benchmarking framework
to validate the Quiz Statistics optimization.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from performance.benchmark_runner import BenchmarkRunner, BenchmarkConfig
from performance.query_counter import QueryCounter
from app.db.engine import engine, db_session
from app.api.auth import TokenData


def quiz_statistics_original(db, category_slug, current_user):
    """
    Original N+1 implementation of Quiz Statistics.

    This is the original implementation that executes N+1 queries.
    """
    from app.models.user import User
    from app.models.lesson_block import LessonBlock
    from app.models.course_module import CourseModule
    from app.models.course import Course
    from app.models.learner_event import LearnerEvent

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

    rows = []
    for learner in learners:
        learner_attempts = []
        for block, module, course in quiz_blocks:
            # N+1: Query history for each (learner, block) combination
            events = db.query(LearnerEvent).filter(
                LearnerEvent.user_id == learner.id,
                LearnerEvent.org_id == current_user.org_id,
                LearnerEvent.course_id == course.id,
                LearnerEvent.block_id == block.id,
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

            settings = block.metadata_json or {}
            max_attempts = settings.get("max_attempts", settings.get("attempt_limit", 0))
            try:
                max_attempts = int(max_attempts or 0)
            except (TypeError, ValueError):
                max_attempts = 0
            max_attempts = max_attempts if max_attempts > 0 else None

            attempts_used = len(history)
            attempts_remaining = None if max_attempts is None else max(max_attempts - attempts_used, 0)
            highest_score = max((attempt["score"] for attempt in history), default=0.0)
            latest_score = history[-1]["score"] if history else None
            best_attempt = max(history, key=lambda item: item["score"], default=None)
            average_score = sum(attempt["score"] for attempt in history) / attempts_used if attempts_used else 0.0
            completion_status = "completed" if any(attempt["passed"] for attempt in history) else "attempted" if history else "not_started"

            learner_attempts.append({
                "course_id": course.id,
                "course_name": course.name,
                "module_id": module.id,
                "module_title": module.title,
                "block_id": block.id,
                "quiz_title": block.content or settings.get("title") or "Quiz",
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


def quiz_statistics_optimized(db, category_slug, current_user):
    """
    Optimized batch-query implementation of Quiz Statistics.

    This is the optimized implementation that uses batch queries.
    """
    from app.models.user import User
    from app.models.lesson_block import LessonBlock
    from app.models.course_module import CourseModule
    from app.models.course import Course
    from app.models.learner_event import LearnerEvent

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

    # Collect all learner IDs, block IDs, and course IDs for batch query
    learner_ids = [learner.id for learner in learners]
    block_info = {(block.id, course.id): (block, module, course) for block, module, course in quiz_blocks}
    course_ids = {course.id for _, _, course in quiz_blocks}

    # Batch fetch all LearnerEvent records for all (learner, block, course) combinations
    all_events = db.query(LearnerEvent).filter(
        LearnerEvent.user_id.in_(learner_ids),
        LearnerEvent.org_id == current_user.org_id,
        LearnerEvent.course_id.in_(course_ids),
        LearnerEvent.event_type == "QUIZ_SUBMITTED",
        LearnerEvent.block_id.in_(block_info.keys())
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
            max_attempts = settings.get("max_attempts", settings.get("attempt_limit", 0))
            try:
                max_attempts = int(max_attempts or 0)
            except (TypeError, ValueError):
                max_attempts = 0
            max_attempts = max_attempts if max_attempts > 0 else None

            attempts_used = len(history)
            attempts_remaining = None if max_attempts is None else max(max_attempts - attempts_used, 0)
            highest_score = max((attempt["score"] for attempt in history), default=0.0)
            latest_score = history[-1]["score"] if history else None
            best_attempt = max(history, key=lambda item: item["score"], default=None)
            average_score = sum(attempt["score"] for attempt in history) / attempts_used if attempts_used else 0.0
            completion_status = "completed" if any(attempt["passed"] for attempt in history) else "attempted" if history else "not_started"

            learner_attempts.append({
                "course_id": course.id,
                "course_name": course.name,
                "module_id": module.id,
                "module_title": module.title,
                "block_id": block.id,
                "quiz_title": block.content or settings.get("title") or "Quiz",
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


def main():
    """Run the benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark Quiz Statistics Endpoint")
    parser.add_argument("--category-slug", required=True, help="Category slug to test")
    parser.add_argument("--org-id", required=True, type=int, help="Organization ID")
    parser.add_argument("--user-id", required=True, help="User ID for authentication")
    parser.add_argument("--runs", type=int, default=5, help="Number of benchmark runs")
    parser.add_argument("--output", default="quiz_statistics_benchmark.json", help="Output file")

    args = parser.parse_args()

    # Initialize
    query_counter = QueryCounter()
    query_counter.attach_to_engine(engine)
    runner = BenchmarkRunner(query_counter)

    # Setup test data
    category_slug = args.category_slug
    org_id = args.org_id
    user_id = args.user_id

    # Create mock token
    current_user = TokenData(
        id=user_id,
        email="test@example.com",
        role="category_admin",
        org_id=org_id,
        category_scope=category_slug,
        is_platform_admin=False,
    )

    # Create benchmark config
    config = BenchmarkConfig(
        name="quiz_statistics",
        implementation1=lambda: quiz_statistics_original(db, category_slug, current_user),
        implementation2=lambda: quiz_statistics_optimized(db, category_slug, current_user),
        description="Quiz Statistics endpoint - N+1 to batch query optimization",
        runs=args.runs,
        warmup_runs=1,
    )

    # Run benchmark
    print("="*60)
    print("Quiz Statistics Benchmark")
    print("="*60)
    print(f"Category: {category_slug}")
    print(f"Organization ID: {org_id}")
    print(f"User ID: {user_id}")
    print(f"Runs: {args.runs}")
    print(f"Output: {args.output}")

    try:
        with db_session() as db:
            result = runner.run_benchmark(config)
            runner.print_summary()
            runner.generate_report(args.output)

        print(f"\n✅ Benchmark complete. Results saved to: {args.output}")

    except Exception as e:
        print(f"\n❌ Error during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
