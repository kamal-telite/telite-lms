"""Gradebook Core G0.2 helper service.

This service records current item-level grade results only. It does not
aggregate final course grades or evaluate completion policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_progress import CourseProgress
from app.models.gradebook import GradeItem, GradeResult
from app.models.lesson_block import LessonBlock


DEFAULT_GRADING_POLICY = {
    "attempt_strategy": "best",
    "missing_policy": "exclude_until_due",
    "late_policy": "none",
}


class GradebookService:
    def __init__(self, session: Session):
        self.session = session

    def course_version_token(self, *, user_id: str, course_id: str, org_id: int) -> str:
        progress = self.session.execute(
            select(CourseProgress).where(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id,
                CourseProgress.org_id == org_id,
            )
        ).scalar_one_or_none()
        if progress and progress.enrolled_version is not None:
            return str(progress.enrolled_version)
        return "current"

    @staticmethod
    def quiz_points_possible(settings: dict[str, Any]) -> float:
        questions = settings.get("questions") or []
        return float(sum(int(question.get("points") or 1) for question in questions) or 100)

    @staticmethod
    def assignment_points_possible(block: LessonBlock) -> float:
        settings = block.metadata_json or {}
        return float(settings.get("points_possible") or settings.get("max_points") or 100)

    def ensure_quiz_grade_item(
        self,
        *,
        org_id: int,
        course_id: str,
        block_id: int,
        title: str,
        settings: dict[str, Any],
        actor_user_id: str,
    ) -> GradeItem:
        return self._ensure_grade_item(
            org_id=org_id,
            course_id=course_id,
            source_type="quiz_block",
            source_id=str(block_id),
            title=title,
            points_possible=self.quiz_points_possible(settings),
            actor_user_id=actor_user_id,
            grading_policy={**DEFAULT_GRADING_POLICY, "attempt_strategy": "best"},
        )

    def ensure_assignment_grade_item(
        self,
        *,
        org_id: int,
        course: Course,
        block: LessonBlock,
        actor_user_id: str,
    ) -> GradeItem:
        title = block.content or (block.metadata_json or {}).get("title") or "Assignment"
        return self._ensure_grade_item(
            org_id=org_id,
            course_id=course.id,
            source_type="assignment_block",
            source_id=str(block.id),
            title=title,
            points_possible=self.assignment_points_possible(block),
            actor_user_id=actor_user_id,
            grading_policy={**DEFAULT_GRADING_POLICY, "attempt_strategy": "latest"},
        )

    def _ensure_grade_item(
        self,
        *,
        org_id: int,
        course_id: str,
        source_type: str,
        source_id: str,
        title: str,
        points_possible: float,
        actor_user_id: str,
        grading_policy: dict[str, Any],
    ) -> GradeItem:
        item = self.session.execute(
            select(GradeItem).where(
                GradeItem.org_id == org_id,
                GradeItem.course_id == course_id,
                GradeItem.source_type == source_type,
                GradeItem.source_id == source_id,
            )
        ).scalar_one_or_none()
        if item:
            item.title = title
            item.points_possible = points_possible
            item.grading_policy_json = {**(item.grading_policy_json or {}), **grading_policy}
            item.updated_by = actor_user_id
            return item

        item = GradeItem(
            org_id=org_id,
            course_id=course_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            points_possible=points_possible,
            is_required=True,
            is_extra_credit=False,
            is_released=False,
            grading_policy_json=grading_policy,
            sort_order=0,
            created_by=actor_user_id,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def upsert_current_result(
        self,
        *,
        org_id: int,
        course_id: str,
        course_version_id: str,
        grade_item: GradeItem,
        user_id: str,
        source_type: str,
        source_id: str | None,
        attempt_number: int | None,
        points_awarded: float | None,
        points_possible: float,
        percentage: float | None,
        status: str,
        graded_by: str | None,
        graded_at: datetime | None,
        feedback: str | None,
        metadata: dict[str, Any],
    ) -> GradeResult:
        existing = self.session.execute(
            select(GradeResult).where(
                GradeResult.org_id == org_id,
                GradeResult.course_version_id == course_version_id,
                GradeResult.grade_item_id == grade_item.id,
                GradeResult.user_id == user_id,
            )
        ).scalar_one_or_none()

        if existing and not self._should_replace(existing, grade_item, percentage):
            existing.metadata_json = {
                **(existing.metadata_json or {}),
                "latest_ignored_attempt": metadata,
            }
            self.session.flush()
            return existing

        result = existing or GradeResult(
            org_id=org_id,
            course_id=course_id,
            course_version_id=course_version_id,
            grade_item_id=grade_item.id,
            user_id=user_id,
        )
        if existing is None:
            self.session.add(result)

        result.source_type = source_type
        result.source_id = source_id
        result.attempt_number = attempt_number
        result.points_awarded = points_awarded
        result.points_possible = points_possible
        result.percentage = percentage
        result.status = status
        result.is_current = True
        result.graded_by = graded_by
        result.graded_at = graded_at
        result.feedback = feedback
        result.metadata_json = metadata
        self.session.flush()
        return result

    @staticmethod
    def _should_replace(existing: GradeResult, grade_item: GradeItem, percentage: float | None) -> bool:
        strategy = (grade_item.grading_policy_json or {}).get("attempt_strategy", "best")
        if strategy == "best":
            if percentage is None:
                return False
            if existing.percentage is None:
                return True
            return percentage >= existing.percentage
        return True


def get_course_for_block(session: Session, block_id: int, org_id: int) -> tuple[LessonBlock, CourseModule, Course] | None:
    return session.execute(
        select(LessonBlock, CourseModule, Course)
        .join(CourseModule, LessonBlock.module_id == CourseModule.id)
        .join(Course, CourseModule.course_id == Course.id)
        .where(
            LessonBlock.id == block_id,
            LessonBlock.org_id == org_id,
            CourseModule.org_id == org_id,
            Course.org_id == org_id,
            LessonBlock.deleted_at.is_(None),
            CourseModule.deleted_at.is_(None),
        )
    ).first()
