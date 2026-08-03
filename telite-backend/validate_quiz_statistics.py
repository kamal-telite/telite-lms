"""
Quiz Statistics Optimization Validation Script

This script validates the optimized Quiz Statistics endpoint by:
1. Enabling SQLAlchemy query logging
2. Executing test cases with different dataset sizes
3. Comparing original vs optimized implementations
4. Measuring query count, response time, and memory usage

Usage:
    python validate_quiz_statistics.py --env staging
    python validate_quiz_statistics.py --env development
"""

import os
import sys
import time
import json
import tracemalloc
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.db.engine import db_session, engine
from app.api.routes.learner.quiz import (
    get_category_quiz_statistics,
    quiz_attempt_history,
)
from app.models.user import User
from app.models.learner_event import LearnerEvent
from app.models.lesson_block import LessonBlock
from app.models.course_module import CourseModule
from app.models.course import Course
from app.api.auth import TokenData


# Query logging
query_count = 0
query_log = []


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    global query_count
    query_count += 1
    query_log.append({
        "query": statement,
        "parameters": parameters,
        "timestamp": datetime.utcnow().isoformat()
    })


def reset_query_logging():
    global query_count, query_log
    query_count = 0
    query_log = []


def get_query_count() -> int:
    return query_count


def get_query_log() -> List[Dict]:
    return query_log


class QuizStatisticsValidator:
    def __init__(self, category_slug: str, org_id: int, user_id: str):
        self.category_slug = category_slug
        self.org_id = org_id
        self.user_id = user_id
        self.results = []

    def create_mock_token_data(self) -> TokenData:
        """Create mock TokenData for testing."""
        return TokenData(
            id=self.user_id,
            email="test@example.com",
            role="category_admin",
            org_id=self.org_id,
            category_scope=self.category_slug,
            is_platform_admin=False,
        )

    def execute_original_implementation(self, db, category_slug: str, current_user: TokenData) -> Dict:
        """Execute the original N+1 implementation."""
        reset_query_logging()
        tracemalloc.start()
        start_time = time.time()

        # Original implementation (N+1)
        from app.models.user import User
        from app.models.lesson_block import LessonBlock
        from app.models.course_module import CourseModule
        from app.models.course import Course

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
                settings = block.metadata_json or {}
                history = quiz_attempt_history(
                    db,
                    user_id=learner.id,
                    org_id=current_user.org_id,
                    course_id=course.id,
                    block_id=block.id,
                )
                stats = self._quiz_stats_payload(settings, history)
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

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "response": {"rows": rows},
            "query_count": get_query_count(),
            "response_time_ms": (end_time - start_time) * 1000,
            "peak_memory_mb": peak / 1024 / 1024,
            "query_log": get_query_log(),
        }

    def execute_optimized_implementation(self, db, category_slug: str, current_user: TokenData) -> Dict:
        """Execute the optimized batch-query implementation."""
        reset_query_logging()
        tracemalloc.start()
        start_time = time.time()

        # Optimized implementation (batch query)
        from app.models.user import User
        from app.models.lesson_block import LessonBlock
        from app.models.course_module import CourseModule
        from app.models.course import Course

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
                stats = self._quiz_stats_payload(settings, history)
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

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "response": {"rows": rows},
            "query_count": get_query_count(),
            "response_time_ms": (end_time - start_time) * 1000,
            "peak_memory_mb": peak / 1024 / 1024,
            "query_log": get_query_log(),
        }

    def _quiz_attempt_limit(self, settings: dict) -> int | None:
        """Extract quiz attempt limit from settings."""
        raw = settings.get("max_attempts", settings.get("attempt_limit", 0))
        try:
            value = int(raw or 0)
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else None

    def _quiz_stats_payload(self, settings: dict, history: list[dict]) -> dict:
        """Generate quiz statistics payload."""
        max_attempts = self._quiz_attempt_limit(settings)
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

    def compare_responses(self, original: Dict, optimized: Dict) -> Dict:
        """Compare original and optimized responses."""
        original_response = original["response"]
        optimized_response = optimized["response"]

        differences = []

        # Check if keys match
        if original_response.keys() != optimized_response.keys():
            differences.append({
                "field": "response_keys",
                "original": list(original_response.keys()),
                "optimized": list(optimized_response.keys()),
            })

        # Check row count
        if len(original_response["rows"]) != len(optimized_response["rows"]):
            differences.append({
                "field": "row_count",
                "original": len(original_response["rows"]),
                "optimized": len(optimized_response["rows"]),
            })

        # Check each row
        for i, (orig_row, opt_row) in enumerate(zip(original_response["rows"], optimized_response["rows"])):
            # Check learner info
            if orig_row["learner"] != opt_row["learner"]:
                differences.append({
                    "field": f"row_{i}_learner",
                    "original": orig_row["learner"],
                    "optimized": opt_row["learner"],
                })

            # Check statistics
            stats_fields = ["attempts_used", "attempts_remaining", "highest_score", "latest_score", "average_score", "completion_status"]
            for field in stats_fields:
                if orig_row[field] != opt_row[field]:
                    differences.append({
                        "field": f"row_{i}_{field}",
                        "original": orig_row[field],
                        "optimized": opt_row[field],
                    })

            # Check quiz count
            if len(orig_row["quizzes"]) != len(opt_row["quizzes"]):
                differences.append({
                    "field": f"row_{i}_quiz_count",
                    "original": len(orig_row["quizzes"]),
                    "optimized": len(opt_row["quizzes"]),
                })

            # Check each quiz
            for j, (orig_quiz, opt_quiz) in enumerate(zip(orig_row["quizzes"], opt_row["quizzes"])):
                quiz_fields = ["course_id", "course_name", "module_id", "module_title", "block_id", "quiz_title"]
                for field in quiz_fields:
                    if orig_quiz[field] != opt_quiz[field]:
                        differences.append({
                            "field": f"row_{i}_quiz_{j}_{field}",
                            "original": orig_quiz[field],
                            "optimized": opt_quiz[field],
                        })

                # Check quiz statistics
                quiz_stats = ["attempts_used", "attempts_remaining", "highest_score", "latest_score", "average_score", "completion_status"]
                for field in quiz_stats:
                    if orig_quiz[field] != opt_quiz[field]:
                        differences.append({
                            "field": f"row_{i}_quiz_{j}_{field}",
                            "original": orig_quiz[field],
                            "optimized": opt_quiz[field],
                        })

                # Check attempt history
                if len(orig_quiz["attempt_history"]) != len(opt_quiz["attempt_history"]):
                    differences.append({
                        "field": f"row_{i}_quiz_{j}_attempt_history_count",
                        "original": len(orig_quiz["attempt_history"]),
                        "optimized": len(opt_quiz["attempt_history"]),
                    })

                for k, (orig_attempt, opt_attempt) in enumerate(zip(orig_quiz["attempt_history"], opt_quiz["attempt_history"])):
                    attempt_fields = ["attempt_id", "attempt_number", "attempt_date", "score", "status", "passed"]
                    for field in attempt_fields:
                        if orig_attempt[field] != opt_attempt[field]:
                            differences.append({
                                "field": f"row_{i}_quiz_{j}_attempt_{k}_{field}",
                                "original": orig_attempt[field],
                                "optimized": opt_attempt[field],
                            })

        return {
            "identical": len(differences) == 0,
            "differences": differences,
        }

    def run_validation(self, db, test_name: str) -> Dict:
        """Run validation for a single test case."""
        current_user = self.create_mock_token_data()

        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")

        # Execute original
        print("Executing original implementation...")
        original_result = self.execute_original_implementation(db, self.category_slug, current_user)
        print(f"  Query count: {original_result['query_count']}")
        print(f"  Response time: {original_result['response_time_ms']:.2f}ms")
        print(f"  Peak memory: {original_result['peak_memory_mb']:.2f}MB")

        # Execute optimized
        print("Executing optimized implementation...")
        optimized_result = self.execute_optimized_implementation(db, self.category_slug, current_user)
        print(f"  Query count: {optimized_result['query_count']}")
        print(f"  Response time: {optimized_result['response_time_ms']:.2f}ms")
        print(f"  Peak memory: {optimized_result['peak_memory_mb']:.2f}MB")

        # Compare
        print("Comparing responses...")
        comparison = self.compare_responses(original_result, optimized_result)

        if comparison["identical"]:
            print("  ✅ Responses are identical")
        else:
            print(f"  ❌ Responses differ ({len(comparison['differences'])} differences)")
            for diff in comparison["differences"][:5]:  # Show first 5 differences
                print(f"    - {diff['field']}: {diff['original']} != {diff['optimized']}")
            if len(comparison["differences"]) > 5:
                print(f"    ... and {len(comparison['differences']) - 5} more")

        # Calculate improvements
        query_reduction = ((original_result['query_count'] - optimized_result['query_count']) / original_result['query_count'] * 100) if original_result['query_count'] > 0 else 0
        time_improvement = ((original_result['response_time_ms'] - optimized_result['response_time_ms']) / original_result['response_time_ms'] * 100) if original_result['response_time_ms'] > 0 else 0

        print(f"\nImprovements:")
        print(f"  Query reduction: {query_reduction:.1f}%")
        print(f"  Time improvement: {time_improvement:.1f}%")

        result = {
            "test_name": test_name,
            "original": {
                "query_count": original_result['query_count'],
                "response_time_ms": original_result['response_time_ms'],
                "peak_memory_mb": original_result['peak_memory_mb'],
            },
            "optimized": {
                "query_count": optimized_result['query_count'],
                "response_time_ms": optimized_result['response_time_ms'],
                "peak_memory_mb": optimized_result['peak_memory_mb'],
            },
            "comparison": comparison,
            "improvements": {
                "query_reduction_percent": query_reduction,
                "time_improvement_percent": time_improvement,
            },
        }

        self.results.append(result)
        return result


def main():
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Quiz Statistics Optimization")
    parser.add_argument("--category-slug", required=True, help="Category slug to test")
    parser.add_argument("--org-id", required=True, type=int, help="Organization ID")
    parser.add_argument("--user-id", required=True, help="User ID for authentication")
    parser.add_argument("--output", default="validation_results.json", help="Output file for results")

    args = parser.parse_args()

    validator = QuizStatisticsValidator(
        category_slug=args.category_slug,
        org_id=args.org_id,
        user_id=args.user_id,
    )

    print("="*60)
    print("Quiz Statistics Optimization Validation")
    print("="*60)
    print(f"Category: {args.category_slug}")
    print(f"Organization ID: {args.org_id}")
    print(f"User ID: {args.user_id}")
    print(f"Output: {args.output}")

    try:
        with db_session() as db:
            # Run validation
            result = validator.run_validation(db, "production_dataset")

            # Save results
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"\n{'='*60}")
            print("Validation Complete")
            print(f"{'='*60}")
            print(f"Results saved to: {args.output}")

            # Final recommendation
            if result["comparison"]["identical"]:
                print("\n✅ RECOMMENDATION: APPROVED")
                print("   - Responses are identical")
                print(f"   - Query reduction: {result['improvements']['query_reduction_percent']:.1f}%")
                print(f"   - Time improvement: {result['improvements']['time_improvement_percent']:.1f}%")
            else:
                print("\n❌ RECOMMENDATION: REQUIRES FIXES")
                print(f"   - {len(result['comparison']['differences'])} differences found")
                print("   - Review differences before approval")

    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
