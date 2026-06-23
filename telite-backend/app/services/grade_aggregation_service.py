"""Gradebook Core G0.3 aggregation service."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gradebook import CourseGrade, GradeCategory, GradeItem, GradeResult, GradingScheme
from app.services.gradebook_service import GradebookService


INCLUDED_RESULT_STATUSES = {"graded", "released", "overridden"}
PROVISIONAL_RESULT_STATUSES = {"pending", "submitted", "missing"}


@dataclass
class AggregationInput:
    item: GradeItem
    result: GradeResult | None


class GradeAggregationService:
    """Materializes final course grades from current version-aware grade results."""

    def __init__(self, session: Session):
        self.session = session
        self.gradebook = GradebookService(session)

    def recalculate_course_grade(
        self,
        *,
        org_id: int,
        course_id: str,
        user_id: str,
        course_version_id: str | None = None,
    ) -> CourseGrade:
        version_id = course_version_id or self.gradebook.course_version_token(
            user_id=user_id,
            course_id=course_id,
            org_id=org_id,
        )
        existing = self._get_course_grade(org_id=org_id, course_id=course_id, user_id=user_id, course_version_id=version_id)
        if existing and existing.status in {"locked", "overridden"}:
            return existing

        scheme = self._get_grading_scheme(org_id)
        inputs = self._aggregation_inputs(org_id=org_id, course_id=course_id, user_id=user_id, course_version_id=version_id)
        calculation = self._calculate(inputs)
        percentage = self._round(calculation["percentage"], scheme.rounding_mode if scheme else "nearest")
        passed, display_grade = self._evaluate_pass_fail(percentage, scheme)

        status = "calculated" if percentage is not None and not calculation["has_ungraded_required_items"] and not calculation["has_missing_required_items"] else "draft"
        grade = existing or CourseGrade(
            org_id=org_id,
            course_id=course_id,
            user_id=user_id,
            course_version_id=version_id,
        )
        if existing is None:
            self.session.add(grade)

        grade.grading_scheme_id = scheme.id if scheme else None
        grade.points_awarded = calculation["points_awarded"]
        grade.points_possible = calculation["points_possible"]
        grade.percentage = percentage
        grade.display_grade = display_grade
        grade.passed = passed if status == "calculated" else None
        grade.status = status
        grade.calculated_at = datetime.now(timezone.utc)
        grade.metadata_json = {
            **calculation["metadata"],
            "grading_scheme_id": scheme.id if scheme else None,
            "pass_threshold": self._pass_threshold(scheme),
            "rounding_mode": scheme.rounding_mode if scheme else "nearest",
        }
        self.session.flush()
        return grade

    def _get_course_grade(self, *, org_id: int, course_id: str, user_id: str, course_version_id: str) -> CourseGrade | None:
        return self.session.execute(
            select(CourseGrade).where(
                CourseGrade.org_id == org_id,
                CourseGrade.course_id == course_id,
                CourseGrade.user_id == user_id,
                CourseGrade.course_version_id == course_version_id,
            )
        ).scalar_one_or_none()

    def _get_grading_scheme(self, org_id: int) -> GradingScheme | None:
        return self.session.execute(
            select(GradingScheme)
            .where(
                GradingScheme.org_id == org_id,
                GradingScheme.deleted_at.is_(None),
                GradingScheme.is_org_default.is_(True),
            )
            .order_by(GradingScheme.id)
        ).scalar_one_or_none()

    def _aggregation_inputs(self, *, org_id: int, course_id: str, user_id: str, course_version_id: str) -> list[AggregationInput]:
        items = self.session.execute(
            select(GradeItem)
            .where(
                GradeItem.org_id == org_id,
                GradeItem.course_id == course_id,
                GradeItem.deleted_at.is_(None),
                GradeItem.is_extra_credit.is_(False),
            )
            .order_by(GradeItem.sort_order, GradeItem.id)
        ).scalars().all()
        results = {
            result.grade_item_id: result
            for result in self.session.execute(
                select(GradeResult).where(
                    GradeResult.org_id == org_id,
                    GradeResult.course_id == course_id,
                    GradeResult.user_id == user_id,
                    GradeResult.course_version_id == course_version_id,
                    GradeResult.is_current.is_(True),
                )
            ).scalars().all()
        }
        return [AggregationInput(item=item, result=results.get(item.id)) for item in items]

    def _calculate(self, inputs: list[AggregationInput]) -> dict[str, Any]:
        included: list[AggregationInput] = []
        missing_ids: list[int] = []
        ungraded_ids: list[int] = []
        excluded_ids: list[int] = []
        missing_required = False
        ungraded_required = False

        for entry in inputs:
            item = entry.item
            result = entry.result
            if result is None:
                missing_ids.append(item.id)
                missing_required = missing_required or item.is_required
                continue
            if result.status == "excused":
                excluded_ids.append(item.id)
                continue
            if result.status in PROVISIONAL_RESULT_STATUSES or result.percentage is None:
                ungraded_ids.append(item.id)
                ungraded_required = ungraded_required or item.is_required
                continue
            if result.status in INCLUDED_RESULT_STATUSES:
                included.append(entry)

        percentage, awarded, possible, category_breakdown = self._calculate_percentage(included)
        return {
            "percentage": percentage,
            "points_awarded": awarded,
            "points_possible": possible,
            "has_missing_required_items": missing_required,
            "has_ungraded_required_items": ungraded_required,
            "metadata": {
                "category_breakdown": category_breakdown,
                "included_grade_item_ids": [entry.item.id for entry in included],
                "excluded_grade_item_ids": excluded_ids,
                "missing_grade_item_ids": missing_ids,
                "ungraded_grade_item_ids": ungraded_ids,
                "has_missing_required_items": missing_required,
                "has_ungraded_required_items": ungraded_required,
                "aggregation_strategy": "category_weighted" if self._has_weighted_categories(included) else "points",
            },
        }

    def _calculate_percentage(self, included: list[AggregationInput]) -> tuple[float | None, float | None, float | None, list[dict[str, Any]]]:
        if not included:
            return None, None, None, []

        if self._has_weighted_categories(included):
            return self._calculate_category_weighted(included)

        awarded = sum(float(entry.result.points_awarded or 0) for entry in included if entry.result)
        possible = sum(float(entry.result.points_possible or entry.item.points_possible or 0) for entry in included if entry.result)
        if possible <= 0:
            return None, awarded, possible, []
        return awarded / possible * 100.0, awarded, possible, []

    def _has_weighted_categories(self, included: list[AggregationInput]) -> bool:
        category_ids = {entry.item.category_id for entry in included if entry.item.category_id is not None}
        if not category_ids:
            return False
        total_weight = self.session.execute(
            select(GradeCategory).where(
                GradeCategory.id.in_(category_ids),
                GradeCategory.deleted_at.is_(None),
                GradeCategory.weight > 0,
            )
        ).scalars().all()
        return bool(total_weight)

    def _calculate_category_weighted(self, included: list[AggregationInput]) -> tuple[float | None, float | None, float | None, list[dict[str, Any]]]:
        category_ids = {entry.item.category_id for entry in included if entry.item.category_id is not None}
        categories = {
            category.id: category
            for category in self.session.execute(
                select(GradeCategory).where(
                    GradeCategory.id.in_(category_ids),
                    GradeCategory.deleted_at.is_(None),
                    GradeCategory.weight > 0,
                )
            ).scalars().all()
        }
        weighted_sum = 0.0
        weight_denominator = 0.0
        total_awarded = 0.0
        total_possible = 0.0
        breakdown: list[dict[str, Any]] = []
        for category_id, category in categories.items():
            entries = [entry for entry in included if entry.item.category_id == category_id and entry.result]
            awarded = sum(float(entry.result.points_awarded or 0) for entry in entries)
            possible = sum(float(entry.result.points_possible or entry.item.points_possible or 0) for entry in entries)
            if possible <= 0:
                continue
            category_percentage = awarded / possible * 100.0
            weighted_sum += category_percentage * float(category.weight)
            weight_denominator += float(category.weight)
            total_awarded += awarded
            total_possible += possible
            breakdown.append(
                {
                    "category_id": category.id,
                    "name": category.name,
                    "weight": category.weight,
                    "percentage": category_percentage,
                    "grade_item_ids": [entry.item.id for entry in entries],
                }
            )
        if weight_denominator <= 0:
            return self._calculate_percentage_without_category_recursion(included)
        return weighted_sum / weight_denominator, total_awarded, total_possible, breakdown

    @staticmethod
    def _calculate_percentage_without_category_recursion(included: list[AggregationInput]) -> tuple[float | None, float | None, float | None, list[dict[str, Any]]]:
        awarded = sum(float(entry.result.points_awarded or 0) for entry in included if entry.result)
        possible = sum(float(entry.result.points_possible or entry.item.points_possible or 0) for entry in included if entry.result)
        if possible <= 0:
            return None, awarded, possible, []
        return awarded / possible * 100.0, awarded, possible, []

    def _evaluate_pass_fail(self, percentage: float | None, scheme: GradingScheme | None) -> tuple[bool | None, str | None]:
        if percentage is None:
            return None, None
        threshold = self._pass_threshold(scheme)
        passed = percentage >= threshold
        scheme_type = scheme.scheme_type if scheme else "percentage"
        if scheme_type == "pass_fail":
            return passed, "Pass" if passed else "Fail"
        if scheme_type == "letter":
            return passed, self._letter_display(percentage, scheme.scale_json if scheme else None)
        return passed, f"{percentage:.2f}%"

    @staticmethod
    def _pass_threshold(scheme: GradingScheme | None) -> float:
        return float(scheme.default_pass_threshold if scheme else 60.0)

    @staticmethod
    def _letter_display(percentage: float, scale: Any) -> str:
        if not isinstance(scale, list):
            scale = [
                {"min": 90, "label": "A"},
                {"min": 80, "label": "B"},
                {"min": 70, "label": "C"},
                {"min": 60, "label": "D"},
                {"min": 0, "label": "F"},
            ]
        for row in sorted(scale, key=lambda item: float(item.get("min", 0)), reverse=True):
            if percentage >= float(row.get("min", 0)):
                return str(row.get("label", ""))
        return "F"

    @staticmethod
    def _round(value: float | None, mode: str) -> float | None:
        if value is None:
            return None
        if mode == "floor":
            return float(math.floor(value))
        if mode == "ceil":
            return float(math.ceil(value))
        return round(float(value), 2)
