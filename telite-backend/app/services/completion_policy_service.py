"""Policy-driven course completion evaluation for Gradebook G0.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_progress import CourseProgress
from app.models.gradebook import CompletionRule, CourseGrade


CONTENT_COMPLETE_STATUS = "content_complete"
COMPLETED_STATUS = "completed"
IN_PROGRESS_STATUS = "in_progress"
NOT_STARTED_STATUS = "not_started"
PENDING_GRADE_STATUS = "pending_grade"

PASS_SATISFYING_GRADE_STATUSES = {"calculated", "released", "locked", "overridden"}


@dataclass(frozen=True)
class EffectiveCompletionRule:
    org_id: int
    course_id: str
    course_version_id: str | None = None
    rule_id: int | None = None
    requires_content_completion: bool = True
    minimum_content_percentage: float = 100.0
    requires_grade_pass: bool = False
    minimum_final_percentage: float | None = None
    requires_instructor_approval: bool = False
    certificate_eligible_on_completion: bool = True

    @classmethod
    def content_only(cls, *, org_id: int, course_id: str, course_version_id: str | None) -> "EffectiveCompletionRule":
        return cls(org_id=org_id, course_id=course_id, course_version_id=course_version_id)

    @classmethod
    def from_model(cls, rule: CompletionRule, *, course_id: str, course_version_id: str | None) -> "EffectiveCompletionRule":
        return cls(
            org_id=rule.org_id,
            course_id=course_id,
            course_version_id=course_version_id,
            rule_id=rule.id,
            requires_content_completion=rule.requires_content_completion,
            minimum_content_percentage=rule.minimum_content_percentage,
            requires_grade_pass=rule.requires_grade_pass,
            minimum_final_percentage=rule.minimum_final_percentage,
            requires_instructor_approval=rule.requires_instructor_approval,
            certificate_eligible_on_completion=rule.certificate_eligible_on_completion,
        )


@dataclass(frozen=True)
class CompletionEvaluationResult:
    user_id: str
    course_id: str
    org_id: int
    content_progress_percentage: float
    content_complete: bool
    grade_required: bool
    grade_passed: bool | None
    instructor_approval_required: bool
    instructor_approved: bool | None
    completed: bool
    previous_state: str
    new_state: str
    completed_now: bool
    unmet_requirements: list[str] = field(default_factory=list)
    completion_rule_id: int | None = None
    course_grade_id: int | None = None

    def to_event_payload(self) -> dict:
        return {
            "completion_rule_id": self.completion_rule_id,
            "course_grade_id": self.course_grade_id,
            "content_progress_percentage": self.content_progress_percentage,
            "content_complete": self.content_complete,
            "grade_required": self.grade_required,
            "grade_passed": self.grade_passed,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "unmet_requirements": self.unmet_requirements,
        }


@dataclass(frozen=True)
class CourseCompletionReadResult:
    user_id: str
    course_id: str
    org_id: int
    completed: bool
    status: str
    content_progress_percentage: float
    course_progress_id: int | None
    completion_rule_id: int | None
    course_grade_id: int | None
    course_version_id: str | None
    unmet_requirements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CertificateEligibilityResult:
    user_id: str
    course_id: str
    org_id: int
    eligible: bool
    completed: bool
    certificate_eligible_on_completion: bool
    course_progress_id: int | None
    completion_rule_id: int | None
    course_grade_id: int | None
    course_version_id: str | None
    unmet_requirements: list[str] = field(default_factory=list)


class CompletionPolicyError(ValueError):
    """Raised when a completion rule is invalid for G0.4."""


class CompletionPolicyService:
    """Evaluates TELITE course completion without touching certificates or paths."""

    def __init__(self, session: Session):
        self.session = session

    def effective_rule(
        self,
        *,
        org_id: int,
        course_id: str,
        course_version_id: str | None,
    ) -> EffectiveCompletionRule:
        course_rule = self.session.execute(
            select(CompletionRule).where(
                CompletionRule.org_id == org_id,
                CompletionRule.course_id == course_id,
                CompletionRule.course_version_id == course_version_id,
                CompletionRule.status == "active",
                CompletionRule.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if course_rule:
            return self._validated_rule(course_rule, course_id=course_id, course_version_id=course_version_id)

        unversioned_course_rule = self.session.execute(
            select(CompletionRule).where(
                CompletionRule.org_id == org_id,
                CompletionRule.course_id == course_id,
                CompletionRule.course_version_id.is_(None),
                CompletionRule.status == "active",
                CompletionRule.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if unversioned_course_rule:
            return self._validated_rule(unversioned_course_rule, course_id=course_id, course_version_id=course_version_id)

        org_default = self.session.execute(
            select(CompletionRule).where(
                CompletionRule.org_id == org_id,
                CompletionRule.course_id.is_(None),
                CompletionRule.status == "active",
                CompletionRule.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if org_default:
            return self._validated_rule(org_default, course_id=course_id, course_version_id=course_version_id)

        return EffectiveCompletionRule.content_only(
            org_id=org_id,
            course_id=course_id,
            course_version_id=course_version_id,
        )

    def evaluate_course_completion(
        self,
        *,
        user_id: str,
        course_id: str,
        org_id: int,
        course_progress: CourseProgress | None = None,
    ) -> CompletionEvaluationResult:
        progress = course_progress or self.session.execute(
            select(CourseProgress).where(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id,
                CourseProgress.org_id == org_id,
            )
        ).scalar_one_or_none()
        if progress is None:
            raise CompletionPolicyError("CourseProgress is required before completion can be evaluated")

        course_version_id = str(progress.enrolled_version) if progress.enrolled_version is not None else None
        rule = self.effective_rule(
            org_id=org_id,
            course_id=course_id,
            course_version_id=course_version_id,
        )
        previous_state = progress.status
        content_percentage = float(progress.completion_percentage or 0.0)
        content_complete = (
            not rule.requires_content_completion
            or content_percentage >= rule.minimum_content_percentage
        )

        course_grade = self._course_grade(
            org_id=org_id,
            course_id=course_id,
            user_id=user_id,
            course_version_id=course_version_id,
        )
        grade_passed = self._grade_passed(course_grade, rule) if rule.requires_grade_pass else None

        unmet = self._unmet_requirements(progress=progress, rule=rule, course_grade=course_grade)
        new_state = self._new_state(
            previous_state=previous_state,
            content_complete=content_complete,
            rule=rule,
            grade_passed=grade_passed,
        )
        completed_now = previous_state != COMPLETED_STATUS and new_state == COMPLETED_STATUS

        progress.status = new_state
        if new_state == COMPLETED_STATUS:
            progress.completion_percentage = 100.0
            progress.completed_at = progress.completed_at or datetime.now(timezone.utc)
        elif previous_state == COMPLETED_STATUS:
            progress.completed_at = None

        self.session.flush()

        return CompletionEvaluationResult(
            user_id=user_id,
            course_id=course_id,
            org_id=org_id,
            content_progress_percentage=float(progress.completion_percentage or 0.0),
            content_complete=content_complete,
            grade_required=rule.requires_grade_pass,
            grade_passed=grade_passed,
            instructor_approval_required=rule.requires_instructor_approval,
            instructor_approved=None,
            completed=new_state == COMPLETED_STATUS,
            previous_state=previous_state,
            new_state=new_state,
            completed_now=completed_now,
            unmet_requirements=unmet,
            completion_rule_id=rule.rule_id,
            course_grade_id=course_grade.id if course_grade else None,
        )

    def is_course_completed(
        self,
        *,
        user_id: str,
        course_id: str,
        org_id: int,
    ) -> CourseCompletionReadResult:
        """Read academic completion state without mutating CourseProgress."""
        progress = self._course_progress(user_id=user_id, course_id=course_id, org_id=org_id)
        if not progress:
            return CourseCompletionReadResult(
                user_id=user_id,
                course_id=course_id,
                org_id=org_id,
                completed=False,
                status=NOT_STARTED_STATUS,
                content_progress_percentage=0.0,
                course_progress_id=None,
                completion_rule_id=None,
                course_grade_id=None,
                course_version_id=None,
                unmet_requirements=["course_progress"],
            )

        course_version_id = self._course_version_id(progress)
        rule = self.effective_rule(
            org_id=org_id,
            course_id=course_id,
            course_version_id=course_version_id,
        )
        course_grade = self._course_grade(
            org_id=org_id,
            course_id=course_id,
            user_id=user_id,
            course_version_id=course_version_id,
        )
        unmet = self._unmet_requirements(progress=progress, rule=rule, course_grade=course_grade)
        completed = progress.status == COMPLETED_STATUS and not unmet
        return CourseCompletionReadResult(
            user_id=user_id,
            course_id=course_id,
            org_id=org_id,
            completed=completed,
            status=progress.status,
            content_progress_percentage=float(progress.completion_percentage or 0.0),
            course_progress_id=progress.id,
            completion_rule_id=rule.rule_id,
            course_grade_id=course_grade.id if course_grade else None,
            course_version_id=course_version_id,
            unmet_requirements=unmet,
        )

    def is_certificate_eligible(
        self,
        *,
        user_id: str,
        course_id: str,
        org_id: int,
    ) -> CertificateEligibilityResult:
        """Read certificate eligibility without issuing certificates or notifications."""
        completion = self.is_course_completed(user_id=user_id, course_id=course_id, org_id=org_id)
        rule = self.effective_rule(
            org_id=org_id,
            course_id=course_id,
            course_version_id=completion.course_version_id,
        )
        unmet = list(completion.unmet_requirements)
        if not rule.certificate_eligible_on_completion:
            unmet.append("certificate_eligible_on_completion")
        eligible = completion.completed and rule.certificate_eligible_on_completion
        return CertificateEligibilityResult(
            user_id=user_id,
            course_id=course_id,
            org_id=org_id,
            eligible=eligible,
            completed=completion.completed,
            certificate_eligible_on_completion=rule.certificate_eligible_on_completion,
            course_progress_id=completion.course_progress_id,
            completion_rule_id=completion.completion_rule_id,
            course_grade_id=completion.course_grade_id,
            course_version_id=completion.course_version_id,
            unmet_requirements=unmet,
        )

    def _validated_rule(
        self,
        rule: CompletionRule,
        *,
        course_id: str,
        course_version_id: str | None,
    ) -> EffectiveCompletionRule:
        effective = EffectiveCompletionRule.from_model(rule, course_id=course_id, course_version_id=course_version_id)
        self.validate_rule(effective)
        return effective

    @staticmethod
    def validate_rule(rule: EffectiveCompletionRule) -> None:
        if rule.requires_instructor_approval:
            raise CompletionPolicyError("Instructor approval completion rules are reserved for a future runtime")
        if not (
            rule.requires_content_completion
            or rule.requires_grade_pass
            or rule.requires_instructor_approval
        ):
            raise CompletionPolicyError("At least one completion condition must be enabled")
        if rule.requires_content_completion and not (0 < rule.minimum_content_percentage <= 100):
            raise CompletionPolicyError("minimum_content_percentage must be greater than 0 and less than or equal to 100")
        if rule.requires_grade_pass and rule.minimum_final_percentage is not None:
            if not (0 <= rule.minimum_final_percentage <= 100):
                raise CompletionPolicyError("minimum_final_percentage must be between 0 and 100")

    def _course_progress(self, *, user_id: str, course_id: str, org_id: int) -> CourseProgress | None:
        return self.session.execute(
            select(CourseProgress).where(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id == course_id,
                CourseProgress.org_id == org_id,
            )
        ).scalar_one_or_none()

    @staticmethod
    def _course_version_id(progress: CourseProgress) -> str | None:
        return str(progress.enrolled_version) if progress.enrolled_version is not None else None

    def _course_grade(
        self,
        *,
        org_id: int,
        course_id: str,
        user_id: str,
        course_version_id: str | None,
    ) -> CourseGrade | None:
        return self.session.execute(
            select(CourseGrade).where(
                CourseGrade.org_id == org_id,
                CourseGrade.course_id == course_id,
                CourseGrade.user_id == user_id,
                CourseGrade.course_version_id == (course_version_id or "current"),
            )
        ).scalar_one_or_none()

    def _unmet_requirements(
        self,
        *,
        progress: CourseProgress,
        rule: EffectiveCompletionRule,
        course_grade: CourseGrade | None,
    ) -> list[str]:
        unmet: list[str] = []
        content_percentage = float(progress.completion_percentage or 0.0)
        content_complete = (
            not rule.requires_content_completion
            or content_percentage >= rule.minimum_content_percentage
        )
        if not content_complete:
            unmet.append("content_complete")
        if rule.requires_grade_pass and not self._grade_passed(course_grade, rule):
            unmet.append("grade_passed")
        if rule.requires_instructor_approval:
            unmet.append("instructor_approval")
        return unmet

    @staticmethod
    def _grade_passed(course_grade: CourseGrade | None, rule: EffectiveCompletionRule) -> bool:
        if not course_grade:
            return False
        if course_grade.status not in PASS_SATISFYING_GRADE_STATUSES:
            return False
        if course_grade.passed is not True:
            return False
        if rule.minimum_final_percentage is not None:
            if course_grade.percentage is None:
                return False
            return course_grade.percentage >= rule.minimum_final_percentage
        return True

    @staticmethod
    def _new_state(
        *,
        previous_state: str,
        content_complete: bool,
        rule: EffectiveCompletionRule,
        grade_passed: bool | None,
    ) -> str:
        if not content_complete:
            return IN_PROGRESS_STATUS if previous_state != NOT_STARTED_STATUS else NOT_STARTED_STATUS
        if rule.requires_grade_pass and not grade_passed:
            return PENDING_GRADE_STATUS
        return COMPLETED_STATUS
