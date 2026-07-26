"""Dynamic PAL score computation.

The service derives PAL metrics from the current native LMS data instead of
requiring separate PAL imports or manual updates on the users table.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.gradebook import GradeResult
from app.models.learner_event import LearnerEvent
from app.models.task_workflow import TaskAssignment
from app.models.user import User


PAL_WEIGHTS = {
    "course_completion": 0.30,
    "quiz_average": 0.30,
    "assignment_average": 0.20,
    "task_completion": 0.20,
}


class PALScoreService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _round(value: float | int | None, places: int = 1) -> float:
        return round(float(value or 0.0), places)

    @staticmethod
    def _clip(value: float | int | None) -> float:
        raw = float(value or 0.0)
        if 0 < raw <= 1:
            raw *= 100.0
        return max(0.0, min(100.0, raw))

    def compute_user_metrics(self, user_id: str, org_id: int) -> dict[str, Any]:
        user = self.session.execute(
            select(User).where(User.id == user_id, User.org_id == org_id)
        ).scalar_one_or_none()
        if not user:
            return self.empty_metrics()

        completion = self._course_completion(user)
        quiz_average = self._quiz_average(user_id, org_id)
        assignment_average = self._assignment_average(user_id, org_id)
        task_completion = self._task_completion(user_id, org_id)
        pal_score = (
            completion * PAL_WEIGHTS["course_completion"]
            + quiz_average * PAL_WEIGHTS["quiz_average"]
            + assignment_average * PAL_WEIGHTS["assignment_average"]
            + task_completion * PAL_WEIGHTS["task_completion"]
        )

        strengths = self._strengths(completion, quiz_average, assignment_average, task_completion)
        weak_areas = self._weak_areas(completion, quiz_average, assignment_average, task_completion)

        metrics = {
            "pal_score": self._round(self._clip(pal_score)),
            "course_completion": self._round(completion),
            "quiz_average": self._round(quiz_average),
            "assignment_average": self._round(assignment_average),
            "task_completion": self._round(task_completion),
            "weights": PAL_WEIGHTS,
            "strengths": strengths,
            "weak_areas": weak_areas,
            "improvements": weak_areas,
            "progress_trend": self._progress_trend(user_id, org_id),
            "completion_timeline": self._completion_timeline(user_id, org_id),
        }
        return metrics

    @classmethod
    def empty_metrics(cls) -> dict[str, Any]:
        return {
            "pal_score": 0.0,
            "course_completion": 0.0,
            "quiz_average": 0.0,
            "assignment_average": 0.0,
            "task_completion": 0.0,
            "weights": PAL_WEIGHTS,
            "strengths": [],
            "weak_areas": ["Course completion", "Quiz average", "Assignment average", "Task completion"],
            "improvements": ["Course completion", "Quiz average", "Assignment average", "Task completion"],
            "progress_trend": [],
            "completion_timeline": [],
        }

    def recompute_user(self, user_id: str, org_id: int, *, commit: bool = False) -> dict[str, Any]:
        user = self.session.execute(
            select(User).where(User.id == user_id, User.org_id == org_id)
        ).scalar_one_or_none()
        if not user:
            return self.empty_metrics()

        metrics = self.compute_user_metrics(user_id, org_id)
        user.pal_score = metrics["pal_score"]
        user.pal_completion_pct = metrics["course_completion"]
        user.pal_quiz_avg = metrics["quiz_average"]
        user.pal_task_completion_pct = metrics["task_completion"]

        progress_rows = self.session.execute(
            select(CourseProgress).where(CourseProgress.user_id == user_id, CourseProgress.org_id == org_id)
        ).scalars().all()
        user.courses_completed = len([row for row in progress_rows if row.status in {"completed", "submitted"} or row.completion_percentage >= 100])
        user.total_courses = max(user.total_courses or 0, len(progress_rows))

        self.session.flush()
        if commit:
            self.session.commit()
        return metrics

    def recompute_category(self, category_slug: str, org_id: int) -> list[dict[str, Any]]:
        users = self.session.execute(
            select(User).where(
                User.role == "learner",
                User.category_scope == category_slug,
                User.org_id == org_id,
            )
        ).scalars().all()
        return [self.recompute_user(user.id, org_id) for user in users]

    def rank_for_user(self, user_id: str, category_slug: str | None, org_id: int) -> int | None:
        if not category_slug:
            return None
        rows = self.session.execute(
            select(User.id).where(
                User.role == "learner",
                User.category_scope == category_slug,
                User.org_id == org_id,
                User.is_active == True,
            ).order_by(User.pal_score.desc(), User.full_name.asc())
        ).scalars().all()
        for index, row_user_id in enumerate(rows, start=1):
            if row_user_id == user_id:
                return index
        return None

    def _course_completion(self, user: User) -> float:
        progress_rows = self.session.execute(
            select(CourseProgress).where(CourseProgress.user_id == user.id, CourseProgress.org_id == user.org_id)
        ).scalars().all()

        course_stmt = select(func.count(Course.id)).where(
            Course.org_id == user.org_id,
            Course.status.in_(("active", "published")),
        )
        if user.category_scope:
            course_stmt = course_stmt.where(Course.category_slug == user.category_scope)
        available_courses = int(self.session.execute(course_stmt).scalar() or 0)

        if progress_rows:
            average = sum(self._clip(row.completion_percentage) for row in progress_rows) / len(progress_rows)
            if available_courses > len(progress_rows):
                return average * (len(progress_rows) / available_courses)
            return average
        return 0.0

    def _quiz_average(self, user_id: str, org_id: int) -> float:
        grade_scores = self.session.execute(
            select(GradeResult.percentage).where(
                GradeResult.user_id == user_id,
                GradeResult.org_id == org_id,
                GradeResult.status == "graded",
                GradeResult.percentage.isnot(None),
                GradeResult.source_type.in_(("quiz_block", "quiz_submission")),
            )
        ).scalars().all()
        if grade_scores:
            return sum(self._clip(score) for score in grade_scores) / len(grade_scores)

        event_scores = []
        events = self.session.execute(
            select(LearnerEvent).where(
                LearnerEvent.user_id == user_id,
                LearnerEvent.org_id == org_id,
                LearnerEvent.event_type == "QUIZ_SUBMITTED",
            )
        ).scalars().all()
        for event in events:
            score = (event.payload_json or {}).get("score")
            if score is not None:
                event_scores.append(self._clip(score))
        return sum(event_scores) / len(event_scores) if event_scores else 0.0

    def _assignment_average(self, user_id: str, org_id: int) -> float:
        grade_scores = self.session.execute(
            select(GradeResult.percentage).where(
                GradeResult.user_id == user_id,
                GradeResult.org_id == org_id,
                GradeResult.status == "graded",
                GradeResult.percentage.isnot(None),
                GradeResult.source_type.in_(("assignment_block", "assignment_submission")),
            )
        ).scalars().all()
        if grade_scores:
            return sum(self._clip(score) for score in grade_scores) / len(grade_scores)

        assignment_scores = self.session.execute(
            select(AssignmentSubmission.grade).where(
                AssignmentSubmission.user_id == user_id,
                AssignmentSubmission.org_id == org_id,
                AssignmentSubmission.grade.isnot(None),
            )
        ).scalars().all()
        return sum(self._clip(score) for score in assignment_scores) / len(assignment_scores) if assignment_scores else 0.0

    def _task_completion(self, user_id: str, org_id: int) -> float:
        statuses = self.session.execute(
            select(TaskAssignment.status).where(
                TaskAssignment.learner_id == user_id,
                TaskAssignment.org_id == org_id,
            )
        ).scalars().all()
        if not statuses:
            return 0.0
        completed = len([status for status in statuses if status in {"approved", "completed"}])
        return completed / len(statuses) * 100.0

    @staticmethod
    def _strengths(completion: float, quiz: float, assignment: float, task: float) -> list[str]:
        values = {
            "Course completion": completion,
            "Quiz average": quiz,
            "Assignment average": assignment,
            "Task completion": task,
        }
        return [name for name, value in values.items() if value >= 75]

    @staticmethod
    def _weak_areas(completion: float, quiz: float, assignment: float, task: float) -> list[str]:
        values = {
            "Course completion": completion,
            "Quiz average": quiz,
            "Assignment average": assignment,
            "Task completion": task,
        }
        return [name for name, value in values.items() if value < 60]

    def _progress_trend(self, user_id: str, org_id: int) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        trend = []
        for offset in range(5, -1, -1):
            start = now - timedelta(days=(offset + 1) * 7)
            end = now - timedelta(days=offset * 7)
            events = self.session.execute(
                select(LearnerEvent).where(
                    LearnerEvent.user_id == user_id,
                    LearnerEvent.org_id == org_id,
                    LearnerEvent.created_at >= start,
                    LearnerEvent.created_at < end,
                    LearnerEvent.event_type.in_(("MODULE_COMPLETED", "QUIZ_SUBMITTED", "COURSE_SUBMITTED", "TASK_APPROVED")),
                )
            ).scalars().all()
            trend.append({"label": f"W{6 - offset}", "value": len(events)})
        return trend

    def _completion_timeline(self, user_id: str, org_id: int) -> list[dict[str, Any]]:
        events = self.session.execute(
            select(LearnerEvent).where(
                LearnerEvent.user_id == user_id,
                LearnerEvent.org_id == org_id,
                LearnerEvent.event_type.in_(("MODULE_COMPLETED", "SECTION_COMPLETED", "COURSE_SUBMITTED", "QUIZ_SUBMITTED")),
            ).order_by(LearnerEvent.created_at.desc()).limit(10)
        ).scalars().all()
        return [
            {
                "type": event.event_type,
                "course_id": event.course_id,
                "module_id": event.module_id,
                "block_id": event.block_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "payload": event.payload_json or {},
            }
            for event in events
        ]
